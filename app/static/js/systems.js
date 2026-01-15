// --- Sound Manager ---
export class SoundManager {
    constructor() {
        this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        this.masterGain = this.ctx.createGain();
        this.masterGain.gain.value = 0.1;
        this.masterGain.connect(this.ctx.destination);
    }

    resume() { if (this.ctx.state === 'suspended') this.ctx.resume(); }

    playHover() {
        this.resume();
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.connect(gain);
        gain.connect(this.masterGain);
        osc.frequency.setValueAtTime(440, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(880, this.ctx.currentTime + 0.1);
        gain.gain.setValueAtTime(0.5, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.1);
        osc.start(); osc.stop(this.ctx.currentTime + 0.1);
    }

    playWarp() {
        this.resume();
        const bufferSize = this.ctx.sampleRate * 2;
        const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
        const data = buffer.getChannelData(0);

        for (let i = 0; i < bufferSize; i++) {
            data[i] = Math.random() * 2 - 1;
        }

        const noise = this.ctx.createBufferSource();
        noise.buffer = buffer;
        const gain = this.ctx.createGain();

        const filter = this.ctx.createBiquadFilter();
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(100, this.ctx.currentTime);
        filter.frequency.exponentialRampToValueAtTime(2000, this.ctx.currentTime + 1);

        noise.connect(filter);
        filter.connect(gain);
        gain.connect(this.masterGain);

        gain.gain.setValueAtTime(0, this.ctx.currentTime);
        gain.gain.linearRampToValueAtTime(1, this.ctx.currentTime + 1);
        gain.gain.linearRampToValueAtTime(0, this.ctx.currentTime + 2);

        noise.start();
    }

    playUnlock() {
        this.resume();
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.type = 'triangle';
        const now = this.ctx.currentTime;
        osc.frequency.setValueAtTime(523.25, now); // C5
        osc.frequency.setValueAtTime(659.25, now + 0.1); // E5
        osc.frequency.setValueAtTime(783.99, now + 0.2); // G5
        osc.frequency.setValueAtTime(1046.50, now + 0.3); // C6

        gain.gain.setValueAtTime(0.3, now);
        gain.gain.linearRampToValueAtTime(0, now + 0.6);

        osc.start();
        osc.stop(now + 0.6);
    }
}

// --- Achievements ---
export class AchievementManager {
    constructor(soundManager) {
        this.sfx = soundManager;
        this.achievements = {
            'first_contact': { title: 'Primeiro Contato', desc: 'Encontrou o UFO e ouviu o sinal.', icon: '🛸' },
            'konami_code': { title: 'Hacker das Galáxias', desc: 'Ativou o código Konami.', icon: '🐱' },
            'theme_master': { title: 'Viajante do Tempo', desc: 'Alternou entre as dimensões (Temas).', icon: '🌗' },
            'explorer': { title: 'Explorador Curioso', desc: 'Visitou todas as seções principais.', icon: '🔭' }
        };
        this.unlocked = JSON.parse(localStorage.getItem('achievements')) || [];
        this.initUI();
    }

    unlock(id) {
        if (!this.unlocked.includes(id) && this.achievements[id]) {
            this.unlocked.push(id);
            localStorage.setItem('achievements', JSON.stringify(this.unlocked));
            this.showToast(this.achievements[id]);
            if (this.sfx) this.sfx.playUnlock();
            this.updateBadge();
        }
    }

    initUI() {
        if (!document.getElementById('achievement-badge')) {
            const badge = document.createElement('div');
            badge.id = 'achievement-badge';
            badge.className = 'fixed bottom-4 left-4 z-50 cursor-pointer group';
            badge.onclick = () => this.toggleAchievements();
            badge.innerHTML = `
                <div class="bg-retro-card border border-retro-accent/30 p-2 rounded-full shadow-[0_0_15px_rgba(0,255,65,0.2)] group-hover:scale-110 transition-transform duration-300">
                    <div class="text-2xl">🏆</div>
                    <div id="achievement-count" class="absolute -top-2 -right-2 bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full border border-retro-bg">0/4</div>
                </div>
            `;
            document.body.appendChild(badge);
        }

        if (!document.getElementById('achievements-modal')) {
            const modal = document.createElement('div');
            modal.id = 'achievements-modal';
            modal.className = 'fixed inset-0 bg-black/80 backdrop-blur-sm z-[60] hidden flex items-center justify-center';
            modal.onclick = (e) => { if (e.target === modal) this.toggleAchievements(); };
            modal.innerHTML = `
                <div class="bg-retro-card border border-retro-accent w-full max-w-md m-4 rounded-xl shadow-[0_0_30px_rgba(0,255,65,0.1)] overflow-hidden">
                    <div class="p-4 border-b border-white/10 flex justify-between items-center bg-white/5">
                        <h3 class="font-mono text-retro-accent text-lg tracking-wider">CONQUISTAS</h3>
                        <button id="close-achievements" class="text-retro-muted hover:text-white transition-colors">✕</button>
                    </div>
                    <div id="achievement-list" class="p-4 space-y-3 max-h-[60vh] overflow-y-auto custom-scrollbar"></div>
                </div>
            `;
            document.body.appendChild(modal);
            document.getElementById('close-achievements').onclick = () => this.toggleAchievements();
        }
        this.updateBadge();
    }

    toggleAchievements() {
        const modal = document.getElementById('achievements-modal');
        modal.classList.toggle('hidden');
        if (!modal.classList.contains('hidden')) this.renderModal();
    }

    renderModal() {
        const list = document.getElementById('achievement-list');
        if (!list) return;
        list.innerHTML = '';
        Object.entries(this.achievements).forEach(([id, data]) => {
            const isUnlocked = this.unlocked.includes(id);
            const item = document.createElement('div');
            item.className = `p-3 rounded border ${isUnlocked ? 'border-retro-accent/50 bg-retro-accent/10' : 'border-white/5 bg-white/5 opacity-50'} flex items-center gap-3`;
            item.innerHTML = `
                <div class="text-2xl ${isUnlocked ? '' : 'grayscale'}">${data.icon}</div>
                <div>
                    <div class="font-bold text-xs ${isUnlocked ? 'text-white' : 'text-retro-muted'}">${data.title}</div>
                    <div class="text-[10px] text-retro-muted">${isUnlocked ? data.desc : '???'}</div>
                </div>
            `;
            list.appendChild(item);
        });
    }

    updateBadge() {
        const count = document.getElementById('achievement-count');
        if (count) count.innerText = `${this.unlocked.length}/${Object.keys(this.achievements).length}`;
    }

    showToast(achievement) {
        const toast = document.createElement('div');
        toast.className = 'fixed top-24 right-6 bg-retro-card border border-yellow-400 text-yellow-400 px-6 py-4 rounded-lg shadow-[0_0_20px_rgba(250,204,21,0.3)] z-50 flex items-center gap-4 transform translate-x-full transition-transform duration-500';
        toast.innerHTML = `
            <div class="text-3xl">${achievement.icon}</div>
            <div>
                <div class="text-xs font-bold tracking-widest uppercase mb-1">Conquista Desbloqueada</div>
                <div class="font-bold text-sm text-white">${achievement.title}</div>
                <div class="text-[10px] text-retro-muted">${achievement.desc}</div>
            </div>
        `;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.remove('translate-x-full'));
        setTimeout(() => {
            toast.classList.add('translate-x-full');
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    }
}
