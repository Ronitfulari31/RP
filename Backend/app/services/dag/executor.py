import logging
import time
import sys
import warnings
import os
import io
import threading
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Callable, Any

# Ensure stdout handles UTF-8 (emojis etc)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

logger = logging.getLogger(__name__)

# Global lock for all pipeline instances to share a single console
_console_lock = threading.Lock()
# Global state for terminal redirection
_silence_lock = threading.Lock()
_silence_count = 0
_original_logging_levels = {}
_old_tqdm_init = None

class NLPDAGExecutor:
    """
    Orchestrator for the DAG-based NLP pipeline.
    Manages execution flow, including sequential, parallel, conditional, and routed steps.
    """

    def __init__(self):
        self.steps = []
        self._current_phase = 1
        self._print_lock = _console_lock

    def _safe_print(self, text: str):
        """Prints text safely even if there are encoding issues."""
        with self._print_lock:
            # SANITIZE: Remove ANY character that might crash a limited terminal (Surrogates and non-BMP)
            # This handles emojis and other non-standard chars that 'charmap' and 'cp1252' hate.
            safe_text = "".join(c for c in text if ord(c) < 0xFFFF and not (0xD800 <= ord(c) <= 0xDFFF))
            
            # Use the current sys.stdout
            out = sys.stdout
        
            try:
                # First attempt: normal write
                out.write(safe_text + "\n")
                out.flush()
            except UnicodeEncodeError:
                try:
                    # Second attempt: encode with replacement for terminal encoding
                    encoded = safe_text.encode(out.encoding or 'utf-8', errors='replace')
                    out.buffer.write(encoded + b'\n')
                    out.buffer.flush()
                except:
                    try:
                        # Third attempt: backslashreplace for the most stubborn terminals
                        encoded = safe_text.encode(out.encoding or 'utf-8', errors='backslashreplace')
                        out.buffer.write(encoded + b'\n')
                        out.buffer.flush()
                    except Exception:
                        # Final fallback: ASCII ignore
                        try:
                            out.write(safe_text.encode('ascii', 'ignore').decode('ascii') + "\n")
                            out.flush()
                        except:
                            pass
            except Exception:
                pass

    @contextmanager
    def _silence_all(self, active: bool):
        """
        Silences chatty libraries and logging if active.
        Thread-safe and avoids global stdout hijacking.
        """
        if not active:
            yield
            return

        global _silence_count, _original_logging_levels, _old_tqdm_init
        
        with _silence_lock:
            if _silence_count == 0:
                # 1. Silence VERY chatty libraries only
                # We specifically leave 'app' and 'dag' alone now to prevent visual blocking
                chatty_libs = [
                    "gliner", "transformers", "huggingface_hub", "urllib3", 
                    "pymongo", "tqdm", "torch", "asyncio", 
                    "pymongo.topology", "sentence_transformers"
                ]
                
                for name in chatty_libs:
                    l = logging.getLogger(name)
                    _original_logging_levels[name] = l.getEffectiveLevel()
                    l.setLevel(logging.ERROR) 
                    l.propagate = False 

                # 🚀 FIX: Silence 'app' and 'dag' INFO noise during visual runs
                # We set to WARNING to allow critical errors through but skip node-level noise
                for name in ["app", "dag"]:
                    l = logging.getLogger(name)
                    _original_logging_levels[name] = l.getEffectiveLevel()
                    l.setLevel(logging.WARNING)

                # 2. Silence tqdm globally (Patched once)
                os.environ["TQDM_DISABLE"] = "1"
                try:
                    from tqdm import tqdm
                    if hasattr(tqdm, '__init__') and _old_tqdm_init is None:
                        _old_tqdm_init = tqdm.__init__
                        def safe_silent_init(self, iterable=None, *args, **kwargs):
                            self.iterable = iterable if iterable is not None else []
                            self.total = len(self.iterable) if hasattr(self.iterable, "__len__") else 0
                            self.n = 0
                            self.fp = None
                            self.disable = True
                            self.desc = kwargs.get("desc", "")
                        tqdm.__init__ = safe_silent_init
                except: pass
                
                # 3. Silence warnings
                warnings.filterwarnings("ignore")
                logging.captureWarnings(True)
            
            _silence_count += 1

        try:
            yield
        finally:
            with _silence_lock:
                if _silence_count > 0:
                    _silence_count -= 1
                
                if _silence_count == 0:
                    # Restore levels
                    for name, level in _original_logging_levels.items():
                        l = logging.getLogger(name)
                        l.setLevel(level)
                        l.propagate = True
                    
                    # Restore tqdm
                    if _old_tqdm_init is not None:
                        try:
                            from tqdm import tqdm
                            tqdm.__init__ = _old_tqdm_init
                            _old_tqdm_init = None
                        except: pass

                    if "TQDM_DISABLE" in os.environ:
                        del os.environ["TQDM_DISABLE"]
                    warnings.resetwarnings()
                    logging.captureWarnings(False)
                    _original_logging_levels = {}
                    
                    # Force a flush of everything to ensure terminal updates
                    sys.stdout.flush()
                    sys.stderr.flush()

    def add_phase_header(self, title: str):
        """Adds a phase header for visual logging."""
        self.steps.append(("phase", title))
        return self

    def add_sequential(self, nodes: List[Any]):
        """Adds a list of nodes to be executed sequentially."""
        self.steps.append(("sequential", nodes))
        return self

    def parallel(self, nodes: List[Any]):
        """Creates a group of nodes to be executed in parallel."""
        return ("parallel", nodes)

    def add_parallel(self, nodes: List[Any]):
        """Adds nodes to be executed in parallel as a step."""
        self.steps.append(self.parallel(nodes))
        return self

    def add_router(self, router_node, routesMap: Dict[str, List[Any]]):
        """Adds a routing step based on the result of a RouterNode."""
        self.steps.append(("router", router_node, routesMap))
        return self

    def add_conditional(self, condition: Callable[[Dict], bool], then_steps: List[Any]):
        """Adds conditional steps that run only if the condition is met."""
        self.steps.append(("conditional", condition, then_steps))
        return self

    def run(self, context: Dict, visual: bool = False) -> Dict:
        """Executes the pipeline steps."""
        start_time = time.time()
        doc_id = str(context.get("document_id", "Unknown"))
        short_id = f"[{doc_id[:10]}...]" if len(doc_id) > 10 else f"[{doc_id}]"
        
        # 🛡️ FIX 2: Re-entry Guard
        if context.get("_pipeline_started"):
            logger.warning(f"[{doc_id}] ⚠️ Pipeline already started for this context. Blocking re-entry.")
            return context
        context["_pipeline_started"] = True

        context["visual_mode"] = visual
        
        # 🧠 FIX 5: Logging Clarity
        trigger = context.get("metadata", {}).get("source") or context.get("source", "unknown")
        logger.info("-" * 60)
        logger.info(f"🚀 PIPELINE START | doc_id={doc_id} | trigger={trigger}")
        logger.info("-" * 60)

        with self._silence_all(visual):
            if visual:
                self._safe_print(f"\n{short_id} 🚀 DAG PIPELINE START")
                self._safe_print("-" * 60)
            else:
                logger.info(f"[{doc_id}] \u25b6 DAG Pipeline Started")
            
            try:
                for step in self.steps:
                    if context.get("rejected"):
                        break
                    
                    context = self._execute_step(step, context)
                    if context is None:
                        if not visual:
                            logger.error(f"[{doc_id}] A node returned None, stopping pipeline.")
                        break
            except Exception as e:
                # Should not happen at executor level normally, but for safety:
                if visual:
                    self._safe_print(f"{short_id} ❌ Pipeline Critical Failure: {str(e)}")
                else:
                    logger.exception(f"[{doc_id}] Executor Crash: {e}")
                context["rejected"] = True
                context["rejection_reason"] = f"Executor Crash: {str(e)}"

        # Calculate total execution time
        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)
        
        # Add requested debugging fields
        context["execution_time_ms"] = execution_time_ms
        context["failed_gate"] = context.get("rejected_at_node") if context.get("rejected") else None
        context["processing_path"] = context.get("processing_mode", "full")

        if context.get("rejected"):
            if visual:
                self._safe_print("-" * 60)
                self._safe_print(f"{short_id} ❌ Pipeline Rejected at {context['failed_gate']} | Reason: {context['rejection_reason']}")
            else:
                logger.warning(f"[{doc_id}] \u274c Pipeline Rejected at {context['failed_gate']} | Reason: {context['rejection_reason']}")
        else:
            if visual:
                self._safe_print("-" * 60)
                self._safe_print(f"{short_id} ✅ PIPELINE SUCCESSFUL ({execution_time_ms}ms)")
            else:
                logger.info(f"[{doc_id}] \u2705 Pipeline Completed ({execution_time_ms}ms) | Path: {context['processing_path']} | Tier: {context.get('tier')}")
            
        return context

    def _execute_step(self, step, context: Dict) -> Dict:
        step_type = step[0]
        doc_id = context.get("document_id", "Unknown")

        if step_type == "phase":
            if context.get("visual_mode"):
                self._safe_print(f"\n" + "=" * 60)
                self._safe_print(f"PHASE {self._current_phase}: {step[1].upper()}")
                self._safe_print("=" * 60)
                self._current_phase += 1
            return context

        if step_type == "sequential":
            for item in step[1]:
                if isinstance(item, tuple):
                    context = self._execute_step(item, context)
                else:
                    context = self._run_node(item, context)
                
                if context.get("rejected"):
                    break
            return context

        elif step_type == "parallel":
            nodes = step[1]
            if context.get("visual_mode"):
                short_id = f"[{str(context.get('document_id', 'Unknown'))[:10]}...]"
                self._safe_print(f"  {short_id} ⚡ Parallel Group: START")
                # Group starts - individual node STARTs handled in _run_parallel
            else:
                logger.info(f"[{doc_id}] \u21c9 Running parallel group: {', '.join([n.name for n in nodes])}")
            return self._run_parallel(nodes, context)

        elif step_type == "router":
            router_node = step[1]
            routes = step[2]
            
            visual = context.get("visual_mode")
            if visual:
                short_id = f"[{str(context.get('document_id', 'Unknown'))[:10]}...]"
                self._safe_print(f"  {short_id} {self._get_node_icon(router_node)} {router_node.name}: START")
                
            route_key = router_node.run(context)
            
            if visual:
                short_id = f"[{str(context.get('document_id', 'Unknown'))[:10]}...]"
                reason = ""
                if "LanguageRouter" in router_node.name:
                    lang = context.get("language", "en")
                    if route_key == "skip_translation":
                        reason = f" | {lang.upper()} article" if lang == "en" else f" | Lang: {lang}"
                        if lang != "en":
                            reason += " (No translation required)"
                    else:
                        reason = f" | From {lang.upper()} to EN"
                
                summary = f"Selected: {route_key}{reason}"
                self._safe_print(f"  {short_id} {self._get_node_icon(router_node)} {router_node.name}: COMPLETED ({summary})")
            else:
                logger.info(f"[{doc_id}] \ud83d\udd00 Router {router_node.name} selected branch: {route_key}")
            
            branch_steps = routes.get(route_key, [])
            for branch_step in branch_steps:
                if isinstance(branch_step, tuple): 
                    context = self._execute_step(branch_step, context)
                else: 
                    context = self._run_node(branch_step, context)
                
                if context.get("rejected"):
                    break
            return context

        elif step_type == "conditional":
            condition = step[1]
            then_steps = step[2]
            if condition(context):
                # logger.info(f"[{doc_id}] \u21b3 Condition met, executing branch")
                for cond_step in then_steps:
                    if isinstance(cond_step, tuple):
                        context = self._execute_step(cond_step, context)
                    else:
                        context = self._run_node(cond_step, context)
                    
                    if context.get("rejected"):
                        break
            return context

        return context

    def _run_node(self, node, context: Dict) -> Dict:
        doc_id = str(context.get("document_id", "Unknown"))
        short_id = f"[{doc_id[:10]}...]" if len(doc_id) > 10 else f"[{doc_id}]"
        visual = context.get("visual_mode")
        start_time = time.time()
        
        try:
            if visual:
                self._safe_print(f"  {short_id} {self._get_node_icon(node)} {node.name}: START")
            else:
                indicator = "\u25cf"
                if "Gate" in node.name: indicator = "\ud83d\udee1\ufe0f"
                logger.info(f"[{doc_id}]   {indicator} {node.name}")
            
            result = node.run(context)
            duration = time.time() - start_time
            
            if result is None:
                context["rejected"] = True
                context["rejection_reason"] = f"Gate {node.name} rejected input"
                context["rejected_at_node"] = node.name
                if visual:
                    self._safe_print(f"  {short_id} {self._get_node_icon(node)} {node.name}: REJECTED ({context['rejection_reason']})")
                return context
            
            if visual:
                summary = self._get_node_summary(node, result)
                self._safe_print(f"  {short_id} {self._get_node_icon(node)} {node.name}: COMPLETED ({summary})")
            
            context.setdefault("processing_time", {})[node.name] = duration
            return result
        except Exception as e:
            # CRITICAL: Ensure the exception message itself doesn't cause a Unicode crash
            error_str = "".join(c for c in str(e) if not (0xD800 <= ord(c) <= 0xDFFF))
            if visual:
                self._safe_print(f"  {short_id} {self._get_node_icon(node)} {node.name}: CRASHED ({error_str})")
            else:
                logger.error(f"[{doc_id}] Error in node {node.name}: {error_str}")
            context["rejected"] = True
            context["rejection_reason"] = f"Crash in {node.name}: {error_str}"
            context["rejected_at_node"] = node.name
            return context

    def _get_node_icon(self, node) -> str:
        name = node.name
        if "Gate" in name: return "🛡️ "
        if "Preprocessing" in name: return "🔧 "
        if "Router" in name: return "🔀 "
        if "Translation" in name: return "🌍 "
        if "NER" in name: return "👥 "
        if "Keyword" in name: return "🔑 "
        if "Category" in name or "Classification" in name: return "📊 "
        if "Location" in name: return "🗺️ "
        if "Summarization" in name or "Summary" in name: return "📝 "
        if "Sentiment" in name: return "😊 "
        if "Embedding" in name: return "🔮 "
        return "● "

    def _get_node_summary(self, node, context) -> str:
        """Extract a one-line summary of what the node did."""
        name = node.name
        if "Preprocessing" in name:
            clean_txt = context.get('cleaned_text', context.get('raw_text', ''))
            return f"Lang: {context.get('language')} | Length: {len(str(clean_txt))}"
        if "Deduplication" in name:
            return "Unique article identified"
        if "LanguageConfidence" in name:
            conf = context.get('scores', {}).get('language_confidence')
            if conf is None: conf = context.get('language_confidence', 1.0)
            return f"Confidence: {conf:.2f}"
        if "TextQuality" in name:
            qual = context.get('scores', {}).get('text_quality')
            if qual is None: qual = context.get('text_quality', 0.85)
            return f"Quality: {qual:.2f}"
        if "LanguageRouter" in name:
            lang = context.get('language', 'en')
            mode = context.get('processing_path', 'unknown')
            if lang == 'en': return f"Selected: skip_translation | EN article"
            return f"Selected: {mode} | {lang.upper()} -> EN"
        if "TranslationNode" in name or "Translation" in name:
            return f"Success | Translated to EN"
        if "NER" in name:
            return f"Found {len(context.get('entities', []))} Entities"
        if "Keyword" in name:
            return f"Found {len(context.get('keywords', []))} Keywords"
        if "Category" in name:
            cat = context.get('category') or context.get('existing_category', 'None')
            return f"Category: {cat}"
        if "Location" in name:
            locs = context.get('locations', {})
            if not locs: locs = context.get('existing_locations', {})
            return f"Loc: {locs}"
        if "SummaryQualityGate" in name:
            s_data = context.get('summary', '')
            s_text = ""
            if isinstance(s_data, dict): s_text = s_data.get('en', s_data.get('summary', ''))
            else: s_text = s_data
            count = len(str(s_text).split())
            return f"Generated | {count} words"
        if "Summarization" in name or "Summary" in name:
            return "Passed"
        if "Sentiment" in name:
            s_val = context.get('sentiment', {})
            label = s_val.get('sentiment', s_val.get('label', 'neutral'))
            return f"Sentiment: {label}"
        if "EmbeddingInput" in name:
            txt_len = len(str(context.get('embedding_input', '')))
            return f"Context finalized | Length: {txt_len}"
        if "Embedding" in name:
            vec = context.get('embedding')
            if vec:
                return f"Vector created | Dim: {len(vec)}"
            return "Vector generation failed"
        if "FinalQualityGate" in name:
            return "Stage Validated"
        if "FinalActionRouter" in name:
            return f"Selected: {context.get('tier') or 'mid_tier'}"
        
        return "Passed"

    def _run_parallel(self, nodes: List[Any], context: Dict) -> Dict:
        visual = context.get("visual_mode")
        short_id = f"[{str(context.get('document_id', 'Unknown'))[:10]}...]"
        
        import threading
        self._parallel_lock = threading.Lock()
        self._parallel_msg_count = 0
        total_msgs = len(nodes) * 2 # Each node has START and COMPLETED
        
        def run_isolated(node, ctx_copy):
            icon = self._get_node_icon(node)
            max_retries = 2
            
            for attempt in range(max_retries):
                try:
                    with self._parallel_lock:
                        if visual:
                            prefix = "[RETRY] " if attempt > 0 else ""
                            self._safe_print(f"     ├── {icon}{prefix}{node.name}: START")
                    
                    # 🛡️ THREAD SAFETY: Every node works on its own snapshot
                    # We pass a copy to prevent cross-thread contamination
                    res = node.run(ctx_copy)
                    
                    if res is not None:
                        with self._parallel_lock:
                            if visual:
                                summary = self._get_node_summary(node, res)
                                self._safe_print(f"     ├── {icon}{node.name}: COMPLETED ({summary})")
                        return res
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Parallel node {node.name} failed: {e}")
                    else:
                        time.sleep(1)
            return None

        # Prepare isolated contexts
        # We use copies to avoid Dictionary sizes changing during iteration in threads
        with ThreadPoolExecutor(max_workers=len(nodes)) as executor:
            futures = {executor.submit(run_isolated, node, context.copy()): node for node in nodes}
            
            for future in futures:
                node = futures[future]
                try:
                    res = future.result(timeout=60)
                    if res is None:
                        context["rejected"] = True
                        context["rejected_at_node"] = node.name
                        context["rejection_reason"] = f"Parallel node {node.name} returned None/Failed"
                        continue

                    # 🤝 MERGE STRATEGY: Safely bring local thread updates into the master context
                    # We only merge keys that parallel nodes are expected to modify
                    merge_keys = [
                        "keywords", "entities", "category", "locations", 
                        "event", "sentiment", "summary", "translated_summary",
                        "flags", "scores", "processing_time", "metadata"
                    ]
                    
                    for key in merge_keys:
                        if key not in res: continue
                        
                        val = res[key]
                        try:
                            if isinstance(val, list):
                                # Append unique items (e.g. flags, keywords)
                                master_list = context.setdefault(key, [])
                                if not isinstance(master_list, list):
                                    # Fallback: if master had a non-list, overwrite or wrap
                                    context[key] = [master_list] if master_list else []
                                    master_list = context[key]
                                
                                for item in val:
                                    if item not in master_list:
                                        master_list.append(item)
                                        
                            elif isinstance(val, dict):
                                # Merge dictionaries (e.g. scores, metadata)
                                master_dict = context.setdefault(key, {})
                                if not isinstance(master_dict, dict):
                                    # TYPE MISMATCH: Overwrite master with child dict to avoid crash
                                    logger.warning(f"Merge mismatch key '{key}': Master type {type(master_dict)}, overwriting with dict.")
                                    context[key] = val.copy()
                                else:
                                    master_dict.update(val)
                            else:
                                # Direct overwrite for single values
                                context[key] = val
                        except Exception as e:
                            logger.error(f"Error merging key '{key}' from {node.name}: {e}")

                except TimeoutError:
                    logger.error(f"!!! Parallel node {node.name} timed out")
                    context["rejected"] = True
                    context["rejected_at_node"] = node.name
                    context["rejection_reason"] = "Timeout (60s)"
                except Exception as e:
                    logger.error(f"Parallel group exception in {node.name}: {e}")
                    context["rejected"] = True
                    context["rejected_at_node"] = node.name
                    context["rejection_reason"] = str(e)
        
        return context
