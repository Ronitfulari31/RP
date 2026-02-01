from app.services.dag.executor import NLPDAGExecutor

# Nodes – Preprocessing
from app.services.dag.nodes.preprocessing_node import (
    PreprocessingNode,
    DeduplicationGate,
    LanguageConfidenceGate,
    TextQualityGate
)

# Nodes – Routing
from app.services.dag.nodes.router_node import (
    LanguageRouter,
    ProcessingModeRouter,
    FinalActionRouter
)

# Nodes – Translation
from app.services.dag.nodes.translation_node import (
    TranslationNode,
    TranslationQualityGate
)

# Nodes – NLP Core
from app.services.dag.nodes.nlp_core_node import (
    NERNode,
    KeywordNode,
    NLPQualityGate
)

# Nodes – Analysis
from app.services.dag.nodes.analysis_node import (
    CategoryNode,
    CategoryConfidenceGate,
    LocationNode,
    SummaryNode,
    SummaryQualityGate,
    SentimentNode
)

# Nodes – Embeddings
from app.services.dag.nodes.embeddings_node import (
    EmbeddingInputNode,
    EmbeddingNode,
    EmbeddingQualityGate
)

# Final
from app.services.dag.nodes.final_gate_node import FinalQualityGate

def build_nlp_pipeline():
    """
    Unified Intelligence Pipeline
    Constructs the declarative flow with branching and parallel execution.
    """
    executor = NLPDAGExecutor()

    # PHASE 1: PREPROCESSING
    executor.add_phase_header("PREPROCESSING")
    executor.add_sequential([
        PreprocessingNode(),
        DeduplicationGate(),
        LanguageConfidenceGate(),
        TextQualityGate()
    ])

    # PHASE 2: NER & TRANSLATION
    executor.add_phase_header("NER & TRANSLATION")
    
    # Extract entities from source text BEFORE translation
    executor.add_sequential([
        NERNode()  # Runs on source language (Hindi/Marathi)
    ])
    
    # Then translate using extracted entities
    executor.add_router(
        LanguageRouter(),
        routesMap={
            "translate": [
                TranslationNode(),  # Uses entities_source from NERNode
                TranslationQualityGate()
            ],
            "skip_translation": []
        }
    )

    # PHASE 3: PARALLEL ANALYSIS (OPTIMIZED THROUGHPUT)
    executor.add_phase_header("PARALLEL ANALYSIS")
    
    # 🚀 group all independent analyzer nodes into a parallel block
    # This allows Keywords, Category, Location, and (if full mode) Summary/Sentiment to run concurrently.
    executor.add_parallel([
        KeywordNode(),
        CategoryNode(),
        LocationNode()
    ])

    # Part 3B: Heavy Content Analysis (Conditional: only for 'full' mode)
    executor.add_conditional(
        condition=lambda ctx: ctx["processing_mode"] == "full",
        then_steps=[
            executor.parallel([
                SummaryNode(),
                SentimentNode()
            ])
        ]
    )

    # Note: Confidence gates still run sequentially to ensure data validity
    executor.add_sequential([
        CategoryConfidenceGate(),
        SummaryQualityGate(),
        NLPQualityGate()
    ])

    # PHASE 5: EMBEDDINGS
    executor.add_phase_header("EMBEDDINGS")
    executor.add_sequential([
        EmbeddingInputNode(),
        EmbeddingNode(),
        EmbeddingQualityGate()
    ])

    # PHASE 6: FINAL DECISION
    executor.add_phase_header("FINAL DECISION")
    executor.add_sequential([
        FinalQualityGate()
    ])
    
    executor.add_router(
        FinalActionRouter(),
        routesMap={
            "high_tier": [],
            "mid_tier": [],
            "low_tier": [],
            "reject": []
        }
    )

    return executor
