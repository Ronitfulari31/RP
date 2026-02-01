import { useRef, useEffect } from 'react';

const InteractiveBackground = () => {
    const canvasRef = useRef(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        let width, height;
        let animationFrameId;

        const mousePos = { x: 0, y: 0 };
        const particles = [];
        const sentimentWaves = [];
        const floatingWords = [];
        const keywords = ['sentiment', 'news', 'trends', 'market', 'emotions', 'analysis', 'data', 'insights'];

        const resize = () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            init();
        };

        class Particle {
            constructor() {
                this.reset();
            }

            reset() {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.size = Math.random() * 2 + 1;
                this.speedX = Math.random() * 0.5 - 0.25;
                this.speedY = Math.random() * 0.5 - 0.25;
                this.opacity = Math.random() * 0.5 + 0.2;
            }

            update() {
                this.x += this.speedX;
                this.y += this.speedY;

                const dx = mousePos.x - this.x;
                const dy = mousePos.y - this.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < 150) {
                    const force = (150 - distance) / 150;
                    this.x -= dx * force * 0.02;
                    this.y -= dy * force * 0.02;
                }

                if (this.x < 0) this.x = width;
                if (this.x > width) this.x = 0;
                if (this.y < 0) this.y = height;
                if (this.y > height) this.y = 0;
            }

            draw() {
                ctx.fillStyle = `rgba(100, 150, 255, ${this.opacity})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        class SentimentWave {
            constructor(sentiment) {
                this.sentiment = sentiment;
                this.y = Math.random() * height;
                this.amplitude = Math.random() * 30 + 20;
                this.frequency = Math.random() * 0.01 + 0.005;
                this.speed = Math.random() * 0.3 + 0.1;
                this.offset = 0;
                this.opacity = Math.random() * 0.15 + 0.1;
            }

            update() {
                this.offset += this.speed;
            }

            draw() {
                const color = this.sentiment === 'positive'
                    ? `rgba(34, 197, 94, ${this.opacity})`
                    : `rgba(239, 68, 68, ${this.opacity})`;

                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.beginPath();

                for (let x = 0; x <= width; x += 5) {
                    const y = this.y + Math.sin(x * this.frequency + this.offset) * this.amplitude;
                    if (x === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }

                ctx.stroke();
            }
        }

        class FloatingWord {
            constructor(word) {
                this.word = word;
                this.reset();
            }

            reset() {
                this.x = Math.random() * width;
                this.y = height + 50;
                this.speed = Math.random() * 0.5 + 0.2;
                this.opacity = Math.random() * 0.3 + 0.1;
                this.fontSize = Math.random() * 14 + 10;
            }

            update() {
                this.y -= this.speed;
                if (this.y < -50) {
                    this.reset();
                }
            }

            draw() {
                ctx.font = `${this.fontSize}px Inter, sans-serif`;
                ctx.fillStyle = `rgba(148, 163, 184, ${this.opacity})`;
                ctx.fillText(this.word, this.x, this.y);
            }
        }

        function init() {
            particles.length = 0;
            sentimentWaves.length = 0;
            floatingWords.length = 0;

            const particleCount = width > 768 ? 80 : 40;
            for (let i = 0; i < particleCount; i++) {
                particles.push(new Particle());
            }

            // sentimentWaves.push(new SentimentWave('positive'));
            // sentimentWaves.push(new SentimentWave('positive'));
            // sentimentWaves.push(new SentimentWave('negative'));
            // sentimentWaves.push(new SentimentWave('negative'));

            keywords.forEach((word, i) => {
                const fw = new FloatingWord(word);
                fw.y = (height / keywords.length) * i;
                floatingWords.push(fw);
            });
        }

        function animate() {
            ctx.clearRect(0, 0, width, height);

            sentimentWaves.forEach(wave => {
                wave.update();
                wave.draw();
            });

            particles.forEach((particle, i) => {
                particles.slice(i + 1).forEach(otherParticle => {
                    const dx = particle.x - otherParticle.x;
                    const dy = particle.y - otherParticle.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < 100) {
                        ctx.strokeStyle = `rgba(100, 150, 255, ${0.1 * (1 - distance / 100)})`;
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(particle.x, particle.y);
                        ctx.lineTo(otherParticle.x, otherParticle.y);
                        ctx.stroke();
                    }
                });
            });

            particles.forEach(particle => {
                particle.update();
                particle.draw();
            });

            floatingWords.forEach(word => {
                word.update();
                word.draw();
            });

            animationFrameId = requestAnimationFrame(animate);
        }

        const handleMouseMove = (e) => {
            mousePos.x = e.clientX;
            mousePos.y = e.clientY;
        };

        const handleTouchMove = (e) => {
            if (e.touches.length > 0) {
                mousePos.x = e.touches[0].clientX;
                mousePos.y = e.touches[0].clientY;
            }
        };

        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('touchmove', handleTouchMove);
        window.addEventListener('resize', resize);

        resize();
        animate();

        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('touchmove', handleTouchMove);
            window.removeEventListener('resize', resize);
            cancelAnimationFrame(animationFrameId);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="fixed top-0 left-0 w-full h-full z-0"
            style={{ background: 'linear-gradient(135deg, #020617 0%, #0f172a 50%, #020617 100%)' }}
        />
    );
};

export default InteractiveBackground;
