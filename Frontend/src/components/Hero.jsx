import { motion } from 'framer-motion';

export default function Hero() {
    return (
        <section className="pt-32 pb-12 px-4 text-center">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
            >
                <span className="px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-semibold mb-6 inline-block">
                    AI-Powered News Intelligence
                </span>
                <h1 className="text-5xl md:text-6xl font-extrabold text-gray-900 tracking-tight mb-6">
                    Upload News for <span className="text-primary italic">Instant</span> Analysis
                </h1>
                <p className="text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed">
                    Extract summaries, sentiment, key entities, bias detection, and deeper insights from any article in seconds.
                </p>
            </motion.div>
        </section>
    );
}
