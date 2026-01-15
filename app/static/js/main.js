import { SoundManager, AchievementManager } from './systems.js';
import { SpaceScene } from './scene.js';

// Estado Global
const state = {
    theme: localStorage.getItem('theme') || 'dark',
    themeValue: { val: localStorage.getItem('theme') === 'light' ? 1 : 0 }
};

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    const sfx = new SoundManager();
    const achievements = new AchievementManager(sfx);

    // Scene 3D
    const scene = new SpaceScene('canvas-container', state.themeValue, (objName, position) => {
        const label = document.getElementById('object-label');
        if (objName) {
            label.innerText = objName;
            label.style.opacity = 1;
            if (position) {
                const x = (position.x * .5 + .5) * window.innerWidth;
                const y = (-(position.y * .5) + .5) * window.innerHeight;
                label.style.transform = `translate(${x}px, ${y}px) translate(-50%, -150%)`;
            }
            document.body.style.cursor = 'pointer';
        } else {
            label.style.opacity = 0;
            document.body.style.cursor = 'default';
        }
    }, achievements);

    // UI: Theme Toggle
    const themeBtn = document.getElementById('theme-toggle');
    updateThemeIcon(state.theme === 'light');

    // Apply initial theme class
    if (state.theme === 'light') {
        document.body.classList.add('light-mode');
    }

    themeBtn.addEventListener('click', () => {
        const isLight = document.body.classList.contains('light-mode');
        document.body.classList.toggle('light-mode');
        localStorage.setItem('theme', !isLight ? 'light' : 'dark');
        state.theme = !isLight ? 'light' : 'dark';

        updateThemeIcon(!isLight);
        scene.updateTheme(!isLight); // Notifica a cena 3D
        achievements.unlock('theme_master');
    });

    // UI: Scroll to Top
    const scrollTopBtn = document.getElementById('scroll-top-btn');
    if (scrollTopBtn) {
        scrollTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // Audio Interaction
    document.addEventListener('mouseover', (e) => {
        if (e.target.closest('a') || e.target.closest('button')) sfx.playHover();
    });

    // Easter Egg: Konami Code
    const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
    let konamiIndex = 0;
    document.addEventListener('keydown', (e) => {
        // UFO Trigger
        if (e.key.toLowerCase() === 'u' && e.target.tagName !== 'INPUT') {
            scene.spawnUFO();
        }

        const key = e.key.toLowerCase();
        // Support for 'Up', 'Down', etc. (legacy/non-standard)
        const mappedKey = key.replace('arrow', '');
        const target = konamiCode[konamiIndex].toLowerCase().replace('arrow', '');

        console.log(`Key: ${key} | Target: ${target} | Index: ${konamiIndex}`);

        if (mappedKey === target) {
            konamiIndex++;
            if (konamiIndex === konamiCode.length) {
                console.log("Konami Code Activated!");
                scene.spawnNyanCat();
                achievements.unlock('konami_code');
                konamiIndex = 0;
            }
        } else {
            konamiIndex = (mappedKey === konamiCode[0].toLowerCase().replace('arrow', '')) ? 1 : 0;
        }
    });

    // CLI Logic
    function toggleCLI() {
        const cli = document.getElementById('cli-overlay');
        cli.classList.toggle('hidden');
        if (!cli.classList.contains('hidden')) document.getElementById('cli-input').focus();
    }
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'k') { e.preventDefault(); toggleCLI(); }
        if (e.key === 'Escape') document.getElementById('cli-overlay').classList.add('hidden');
    });

    const commands = {
        help: "Comandos: sobre, projetos, contato, limpar, nyan",
        sobre: "Luan de Paz. Full Stack Engineer.",
        projetos: "Veja a seção de Projetos.",
        contato: "contact@luandepaz.dev",
        limpar: "CLEAR",
        nyan: "NYAN_CAT"
    };

    const cliInput = document.getElementById('cli-input');
    if (cliInput) {
        cliInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                const input = this.value.trim().toLowerCase();
                const history = document.getElementById('cli-history');
                history.innerHTML += `<div class="mb-1"><span class="text-retro-accent">➜</span> ${this.value}</div>`;

                if (commands[input]) {
                    if (commands[input] === "CLEAR") {
                        history.innerHTML = "";
                    } else if (commands[input] === "NYAN_CAT") {
                        history.innerHTML += `<div class="mb-4 text-retro-accent">Meow! 😺🌈</div>`;
                        scene.spawnNyanCat();
                    } else {
                        history.innerHTML += `<div class="mb-4 text-retro-muted">${commands[input]}</div>`;
                    }
                } else if (input !== "") {
                    history.innerHTML += `<div class="mb-4 text-red-400">Comando desconhecido</div>`;
                }
                this.value = "";
                const output = document.getElementById('cli-output');
                output.scrollTop = output.scrollHeight;
            }
        });
    }
});

function updateThemeIcon(isLight) {
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.innerHTML = isLight
            ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />'
            : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />';
    }
}
