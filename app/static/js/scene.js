// Shaders constants
const NEBULA_VERT = `
uniform float time;
uniform float uBass;
varying vec2 vUv;
varying float vDisplacement;

// Simplex noise function
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }
float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy) );
    vec2 x0 = v -   i + dot(i, C.xx);
    vec2 i1;
    i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 )) + i.x + vec3(0.0, i1.x, 1.0 ));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m ;
    m = m*m ;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
}

void main() {
    vUv = uv;
    float t = time * 0.1;
    float noise = snoise(uv * 3.0 + t);
    
    // Vertex Displacement driven by Bass
    vDisplacement = noise * uBass;
    vec3 newPos = position + normal * (vDisplacement * 30.0); // Physical pulse
    
    gl_Position = projectionMatrix * modelViewMatrix * vec4(newPos, 1.0);
}
`;

const NEBULA_FRAG = `
uniform float time;
uniform float uTheme; 
uniform float uSeed;
uniform float uBass;
uniform float uMid;
uniform float uTreble;
varying vec2 vUv;
varying float vDisplacement;

// Simplex noise function (reused for fragment)
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }
float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy) );
    vec2 x0 = v -   i + dot(i, C.xx);
    vec2 i1;
    i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute( permute( i.y + vec3(0.0, i1.y, 1.0 )) + i.x + vec3(0.0, i1.x, 1.0 ));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
    m = m*m ;
    m = m*m ;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * ( a0*a0 + h*h );
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
}

void main() {
    vec2 uv = vUv;
    float t = time * 0.05 + uMid * 0.2; 
    
    float noise = 0.0;
    float scale = 3.0 + uBass * 1.0;
    float opacity = 0.5;
    
    for(int i = 0; i < 4; i++) {
        noise += snoise(uv * scale + t + uSeed + uTreble * 0.2) * opacity;
        scale *= 2.0;
        opacity *= 0.5;
    }

    // Darker, Deeper Palette (V3)
    vec3 deepPurple = vec3(0.02, 0.0, 0.05); // Very dark purple
    vec3 neonPink = vec3(0.3, 0.0, 0.15); // Much less intense pink
    vec3 cyan = vec3(0.0, 0.2, 0.2); // Dark cyan
    vec3 white = vec3(0.4); // Dimmed white

    // Mix based on noise and audio - Reduced intensity
    vec3 color = mix(deepPurple, neonPink, noise + uBass * 0.15); // Reduced bass influence
    color = mix(color, cyan, noise * noise + uMid * 0.15); // Reduced mid influence
    color += white * uTreble * noise * 0.15; // Reduced sparkles

    // Theme mixing (Dark vs Light)
    vec3 lightThemeColor = mix(vec3(0.95), vec3(0.8, 0.9, 1.0), noise);
    vec3 finalColor = mix(color, lightThemeColor, uTheme);

    // Vignette
    float dist = distance(uv, vec2(0.5));
    finalColor *= 1.0 - dist * (1.0 - uBass * 0.2);

    gl_FragColor = vec4(finalColor, 1.0);
}
`;

export class SpaceScene {
    constructor(containerId, themeValue, onObjectHover, achievements) {
        this.container = document.getElementById(containerId);
        this.themeValue = themeValue;
        this.onHover = onObjectHover;
        this.achievements = achievements;
        this.planets = [];
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.ufoAudio = new Audio('/static/audio/radiohead.mp3');
        this.ufoAudio.crossOrigin = "anonymous";
        this.ufoAudio.volume = 0.5;
        this.audioCtx = null;
        this.analyser = null;
        this.dataArray = null;
        this.clock = new THREE.Clock(); // Added clock for smooth animations

        this.bass = 0;
        this.mid = 0;
        this.treble = 0;

        this.init();
        console.log("🌌 Scene JS Version 28 Loaded (Ultra Slow Accretion)");
    }

    init() {
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.camera.position.z = 40;

        this.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.container.appendChild(this.renderer.domElement);

        this.setupPostProcessing();
        this.addObjects();
        // Removed initSpectrum()
        this.animate();

        window.addEventListener('resize', () => this.onResize());
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));
        window.addEventListener('click', (e) => this.onClick(e));

        setInterval(() => this.spawnUFO(), 300000);
        setInterval(() => this.spawnSpaceship(), 8000 + Math.random() * 10000); // Traffic every 8-18s (More frequent)
        this.spawnSpaceship(); // Spawn one immediately
    }

    initAudio() {
        if (this.audioCtx) return;
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const src = this.audioCtx.createMediaElementSource(this.ufoAudio);
        this.analyser = this.audioCtx.createAnalyser();
        this.analyser.fftSize = 512;
        src.connect(this.analyser);
        this.analyser.connect(this.audioCtx.destination);
        this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    }

    addObjects() {
        // 1. Nebula (High Poly for Vertex Displacement)
        const nebulaGeo = new THREE.SphereGeometry(100, 128, 128);
        this.nebulaMat = new THREE.ShaderMaterial({
            vertexShader: NEBULA_VERT,
            fragmentShader: NEBULA_FRAG,
            uniforms: {
                time: { value: 0 },
                uTheme: { value: this.themeValue.val },
                uSeed: { value: Math.random() * 100 },
                uBass: { value: 0 },
                uMid: { value: 0 },
                uTreble: { value: 0 }
            },
            side: THREE.BackSide
        });
        const nebula = new THREE.Mesh(nebulaGeo, this.nebulaMat);
        this.scene.add(nebula);

        // 2. Star Field (New Patterns)
        this.createStarField();

        // 3. Celestial Bodies (Sun, Moon, Black Hole, Wormhole, Asteroid Belt)
        this.createSun();
        this.createBlackHole();
        this.createWormhole();
        this.createAsteroidBelt();

        // 4. Exotic Planets ("No Man's Sky" Style)
        const planetCount = 8;
        for (let i = 0; i < planetCount; i++) {
            this.createExoticPlanet(i);
        }

        // 5. Space Station (Orbiting the 3rd Planet)
        if (this.planets.length > 4) { // Ensure enough planets exist
            // Find a suitable planet (not the sun/bh/wormhole)
            const targetPlanet = this.planets.find(p => p.userData.name && p.userData.name.includes("Planet"));
            if (targetPlanet) {
                this.createSpaceStation(targetPlanet, 1.5);
            }
        }

        // 6. Comet Spawner
        setInterval(() => this.spawnComet(), 15000 + Math.random() * 10000);
        this.spawnComet(); // Spawn one immediately
    }

    createStarField() {
        const starGeometry = new THREE.BufferGeometry();
        const starCount = 10000;
        const posArray = new Float32Array(starCount * 3);
        const colorArray = new Float32Array(starCount * 3);

        const color1 = new THREE.Color(0xffffff); // White
        const color2 = new THREE.Color(0xaaaaff); // Blueish
        const color3 = new THREE.Color(0xffaa00); // Orangeish

        for (let i = 0; i < starCount; i++) {
            const i3 = i * 3;
            // Random distribution but with a bias towards center for "galaxy" feel
            const r = Math.random() * 400;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);

            posArray[i3] = r * Math.sin(phi) * Math.cos(theta);
            posArray[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
            posArray[i3 + 2] = r * Math.cos(phi);

            // Color variation
            const choice = Math.random();
            let c = color1;
            if (choice > 0.8) c = color2;
            else if (choice > 0.9) c = color3;

            colorArray[i3] = c.r;
            colorArray[i3 + 1] = c.g;
            colorArray[i3 + 2] = c.b;
        }

        starGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
        starGeometry.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));

        const starMaterial = new THREE.PointsMaterial({
            size: 0.2, vertexColors: true, transparent: true, opacity: 0.8
        });
        this.starMesh = new THREE.Points(starGeometry, starMaterial);
        this.scene.add(this.starMesh);
    }

    createExoticPlanet(index) {
        // "No Man's Sky" Style Randomization
        const size = Math.random() * 1.5 + 0.5;
        const semiMajorAxis = 20 + index * 8 + Math.random() * 5;
        const semiMinorAxis = semiMajorAxis * (0.8 + Math.random() * 0.2);

        // Vibrant Palettes
        const palettes = [
            { name: "Toxic", c1: 0x00ff00, c2: 0x8800ff }, // Green/Purple
            { name: "Radioactive", c1: 0xffff00, c2: 0xff0000 }, // Yellow/Red
            { name: "Frozen", c1: 0x00ffff, c2: 0xffffff }, // Cyan/White
            { name: "Lush", c1: 0x00aa00, c2: 0x0000ff }, // Green/Blue
            { name: "Scorched", c1: 0xff5500, c2: 0x222222 }, // Orange/Black
            { name: "Exotic", c1: 0xff00ff, c2: 0x00ffff } // Magenta/Cyan
        ];
        const palette = palettes[Math.floor(Math.random() * palettes.length)];

        const geometry = new THREE.SphereGeometry(size, 64, 64);
        const material = new THREE.MeshStandardMaterial({
            map: this.createExoticTexture(palette),
            roughness: 0.6,
            metalness: 0.2
        });
        const planet = new THREE.Mesh(geometry, material);

        // Atmosphere (Glow)
        const atmoGeo = new THREE.SphereGeometry(size * 1.1, 64, 64);
        const atmoMat = new THREE.MeshBasicMaterial({
            color: palette.c1,
            transparent: true,
            opacity: 0.15,
            side: THREE.BackSide
        });
        const atmosphere = new THREE.Mesh(atmoGeo, atmoMat);
        planet.add(atmosphere);

        // Cloud Layer (New)
        if (Math.random() > 0.3) {
            const cloudGeo = new THREE.SphereGeometry(size * 1.05, 64, 64);
            const cloudMat = new THREE.MeshStandardMaterial({
                color: 0xffffff,
                transparent: true,
                opacity: 0.4,
                alphaMap: this.createCloudTexture(),
                side: THREE.DoubleSide
            });
            const clouds = new THREE.Mesh(cloudGeo, cloudMat);
            planet.add(clouds);
            planet.userData.clouds = clouds; // For animation
        }

        // Rings (Double Ring Chance)
        if (Math.random() > 0.6) {
            this.createRing(planet, size, palette.c2, 1.4, 2.2);
            if (Math.random() > 0.5) {
                this.createRing(planet, size, palette.c1, 2.3, 2.8); // Second Ring
            }
        }

        // Moon (High Chance)
        if (Math.random() > 0.3) {
            this.createMoon(planet, size);
        }

        planet.userData = {
            name: `${palette.name} Planet ${index + 1}`,
            semiMajorAxis: semiMajorAxis,
            semiMinorAxis: semiMinorAxis,
            inclination: (Math.random() - 0.5) * 0.8,
            speed: (Math.random() * 0.0005 + 0.0002) * (Math.random() > 0.5 ? 1 : -1),
            angle: Math.random() * Math.PI * 2
        };
        this.scene.add(planet);
        this.planets.push(planet);
    }

    createRing(planet, size, color, innerScale, outerScale) {
        const ringGeo = new THREE.RingGeometry(size * innerScale, size * outerScale, 64);
        const ringMat = new THREE.MeshBasicMaterial({
            color: color,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.4
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2 + (Math.random() - 0.5);
        planet.add(ring);
    }

    createMoon(parent, parentSize) {
        const size = parentSize * (0.5 + Math.random() * 0.3); // Huge Moons (50-80% of parent)
        const dist = parentSize * 5 + Math.random() * 3; // Even further out

        // Moon Types
        const types = [
            { name: "Rocky", color: 0xaaaaaa, rough: 0.7 }, // Brighter grey
            { name: "Ice", color: 0xe0ffff, rough: 0.1, emissive: 0x222222 }, // Slight glow
            { name: "Volcanic", color: 0x550000, rough: 0.8, emissive: 0xff3300, emissiveIntensity: 2.0 } // Bright lava
        ];
        const type = types[Math.floor(Math.random() * types.length)];

        const geo = new THREE.SphereGeometry(size, 32, 32);
        const mat = new THREE.MeshStandardMaterial({
            color: type.color,
            roughness: type.rough,
            emissive: type.emissive || 0x000000,
            emissiveIntensity: type.emissiveIntensity || 0.2
        });
        const moon = new THREE.Mesh(geo, mat);
        moon.userData = { name: type.name }; // Name Tag Support

        const pivot = new THREE.Group();
        pivot.add(moon);
        moon.position.x = dist;
        parent.add(pivot);

        parent.userData.moonPivot = pivot;
        parent.userData.moonSpeed = 0.01 + Math.random() * 0.02;
    }

    createSun() {
        // Randomize Sun Type
        const types = [
            { name: "Yellow Dwarf", color: 0xffaa00, size: 5, intensity: 1.5 },
            { name: "Red Giant", color: 0xff3300, size: 8, intensity: 1.0 },
            { name: "Blue Supergiant", color: 0x00aaff, size: 6, intensity: 2.0 },
            { name: "White Dwarf", color: 0xffffff, size: 2, intensity: 1.2 },
            { name: "Neutron Star", color: 0x00ffff, size: 1.5, intensity: 3.0, pulse: true },
            { name: "Binary Star", color: 0xffaa00, size: 4, intensity: 1.5, binary: true }
        ];
        const type = types[Math.floor(Math.random() * types.length)];
        console.log(`☀️ Spawning Sun Type: ${type.name}`);

        const sunGroup = new THREE.Group();
        sunGroup.userData = { name: type.name }; // Name Tag Support
        this.scene.add(sunGroup);

        if (type.binary) {
            // Binary System
            const sun1 = this.createStarMesh(type.color, type.size);
            const sun2 = this.createStarMesh(0xff3300, type.size * 0.8);
            sun1.position.x = type.size * 1.5;
            sun2.position.x = -type.size * 1.5;
            sunGroup.add(sun1);
            sunGroup.add(sun2);

            // Shared Light
            const light = new THREE.PointLight(type.color, type.intensity, 200);
            sunGroup.add(light);

            // Animate Rotation
            gsap.to(sunGroup.rotation, { y: Math.PI * 2, duration: 20, repeat: -1, ease: "none" });
        } else {
            // Single Star
            const sun = this.createStarMesh(type.color, type.size);
            sunGroup.add(sun);

            const light = new THREE.PointLight(type.color, type.intensity, 200);
            sunGroup.add(light);

            if (type.pulse) {
                gsap.to(light, { intensity: type.intensity * 1.5, duration: 0.1, yoyo: true, repeat: -1 });
                gsap.to(sun.scale, { x: 1.1, y: 1.1, z: 1.1, duration: 0.1, yoyo: true, repeat: -1 });
            }
        }
    }

    createBlackHole() {
        // Hidden Easter Egg - Polar Coordinate Spawning (Fixed Bounds)
        const bhGroup = new THREE.Group();

        // Polar Coordinates: Guaranteed distance from center
        const minRadius = 40;
        const maxRadius = 90;
        const radius = minRadius + Math.random() * (maxRadius - minRadius);
        const angle = Math.random() * Math.PI * 2;

        const x = radius * Math.cos(angle);
        const y = (radius * Math.sin(angle)) * 0.5;
        const z = -60 - Math.random() * 40;

        bhGroup.position.set(x, y, z);

        // 1. Event Horizon (Pure Black Sphere)
        const sphereGeo = new THREE.SphereGeometry(5, 64, 64);
        const sphereMat = new THREE.MeshBasicMaterial({ color: 0x000000 });
        const sphere = new THREE.Mesh(sphereGeo, sphereMat);
        bhGroup.add(sphere);

        // 2. Photon Ring (Glowing Edge)
        const photonGeo = new THREE.RingGeometry(5.05, 5.2, 64);
        const photonMat = new THREE.MeshBasicMaterial({
            color: 0xffffff,
            side: THREE.DoubleSide,
            blending: THREE.AdditiveBlending,
            transparent: true,
            opacity: 0.8
        });
        const photonRing = new THREE.Mesh(photonGeo, photonMat);
        photonRing.lookAt(this.camera.position); // Always face camera
        bhGroup.add(photonRing);

        // 3. Accretion Disk (Textured & Volumetric-ish)
        const diskGeo = new THREE.RingGeometry(6, 22, 128);
        const diskTex = this.createAccretionDiskTexture();
        const diskMat = new THREE.MeshBasicMaterial({
            map: diskTex,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.9,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        const disk = new THREE.Mesh(diskGeo, diskMat);
        disk.rotation.x = Math.PI / 2.5;
        bhGroup.add(disk);

        // Animate Disk Rotation
        gsap.to(disk.rotation, { z: Math.PI * 2, duration: 20, repeat: -1, ease: "none" });

        // 4. Particle Debris Field (Spiraling In)
        const debrisGeo = new THREE.BufferGeometry();
        const debrisCount = 600;
        const debrisPos = new Float32Array(debrisCount * 3);
        const debrisData = []; // Store angle, radius, speed for each particle

        for (let i = 0; i < debrisCount; i++) {
            const r = 10 + Math.random() * 25; // Start further out
            const theta = Math.random() * Math.PI * 2;
            debrisPos[i * 3] = r * Math.cos(theta);
            debrisPos[i * 3 + 1] = (Math.random() - 0.5) * 1.0; // Scatter height
            debrisPos[i * 3 + 2] = r * Math.sin(theta);

            debrisData.push({
                angle: theta,
                radius: r,
                speed: 0.002 + Math.random() * 0.005, // Much slower initial speed
                drift: (Math.random() - 0.5) * 0.02
            });
        }
        debrisGeo.setAttribute('position', new THREE.BufferAttribute(debrisPos, 3));

        const debrisMat = new THREE.PointsMaterial({
            color: 0xffaa00,
            size: 0.3,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending
        });
        const debris = new THREE.Points(debrisGeo, debrisMat);
        debris.rotation.x = Math.PI / 2.5;
        bhGroup.add(debris);

        // Store for animation
        bhGroup.userData.debris = debris;
        bhGroup.userData.debrisData = debrisData;

        bhGroup.userData.name = "Gargantua";
        this.scene.add(bhGroup);
        this.planets.push(bhGroup);
    }

    createAccretionDiskTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 512; canvas.height = 512;
        const ctx = canvas.getContext('2d');
        const center = 256;

        // Radial Gradient for Glow
        const gradient = ctx.createRadialGradient(center, center, 60, center, center, 250);
        gradient.addColorStop(0, 'rgba(0,0,0,0)');
        gradient.addColorStop(0.1, 'rgba(255, 150, 50, 1)'); // Bright Orange
        gradient.addColorStop(0.4, 'rgba(255, 200, 100, 0.8)'); // Gold
        gradient.addColorStop(0.7, 'rgba(200, 50, 0, 0.4)'); // Reddish
        gradient.addColorStop(1, 'rgba(0,0,0,0)');

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 512, 512);

        // Add Swirls/Noise
        ctx.globalCompositeOperation = 'overlay';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        for (let i = 0; i < 80; i++) {
            ctx.beginPath();
            ctx.lineWidth = Math.random() * 4 + 1;
            const r = 70 + Math.random() * 170;
            ctx.arc(center, center, r, 0, Math.PI * 2);
            ctx.stroke();
        }

        return new THREE.CanvasTexture(canvas);
    }

    createWormhole() {
        const whGroup = new THREE.Group();

        // Random Position (Far away)
        const x = (Math.random() - 0.5) * 300;
        const y = (Math.random() - 0.5) * 150;
        const z = -80 - Math.random() * 50;
        whGroup.position.set(x, y, z);

        // Sphere (The "Throat")
        const sphereGeo = new THREE.SphereGeometry(8, 64, 64);
        const sphereMat = new THREE.MeshBasicMaterial({
            map: this.createWormholeTexture(),
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.9
        });
        const sphere = new THREE.Mesh(sphereGeo, sphereMat);
        whGroup.add(sphere);

        // Distortion Ring
        const ringGeo = new THREE.RingGeometry(8, 12, 64);
        const ringMat = new THREE.MeshBasicMaterial({
            color: 0x88ccff,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.3,
            blending: THREE.AdditiveBlending
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.lookAt(this.camera.position);
        whGroup.add(ring);

        whGroup.userData = { name: "Einstein-Rosen Bridge" };
        this.scene.add(whGroup);
        this.planets.push(whGroup);

        // Animate Texture
        gsap.to(sphere.rotation, { y: Math.PI * 2, x: Math.PI, duration: 30, repeat: -1, ease: "none" });
    }

    createWormholeTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 512; canvas.height = 512;
        const ctx = canvas.getContext('2d');

        // Space-time distortion look
        const gradient = ctx.createLinearGradient(0, 0, 512, 512);
        gradient.addColorStop(0, '#000033');
        gradient.addColorStop(0.5, '#4488ff');
        gradient.addColorStop(1, '#ffffff');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 512, 512);

        // Grid lines
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 2;
        for (let i = 0; i <= 512; i += 32) {
            ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, 512); ctx.stroke();
            ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(512, i); ctx.stroke();
        }

        return new THREE.CanvasTexture(canvas);
    }

    createExoticTexture(palette) {
        const canvas = document.createElement('canvas');
        canvas.width = 512; canvas.height = 512;
        const ctx = canvas.getContext('2d');

        // Base
        const c1 = new THREE.Color(palette.c1);
        const c2 = new THREE.Color(palette.c2);

        ctx.fillStyle = `rgb(${c1.r * 255}, ${c1.g * 255}, ${c1.b * 255})`;
        ctx.fillRect(0, 0, 512, 512);

        // Noise Layers
        for (let i = 0; i < 5000; i++) {
            const x = Math.random() * 512;
            const y = Math.random() * 512;
            const w = Math.random() * 100 + 20;
            const h = Math.random() * 50 + 10;

            ctx.fillStyle = `rgba(${c2.r * 255}, ${c2.g * 255}, ${c2.b * 255}, ${Math.random() * 0.2})`;
            ctx.beginPath();
            ctx.ellipse(x, y, w, h, Math.random() * Math.PI, 0, Math.PI * 2);
            ctx.fill();
        }

        return new THREE.CanvasTexture(canvas);
    }

    createStarMesh(color, size) {
        const geo = new THREE.SphereGeometry(size, 64, 64);
        const mat = new THREE.MeshBasicMaterial({ color: color });
        const mesh = new THREE.Mesh(geo, mat);

        // Glow
        const spriteMat = new THREE.SpriteMaterial({
            map: new THREE.CanvasTexture(this.createGlowTexture(color)),
            color: color,
            transparent: true,
            blending: THREE.AdditiveBlending
        });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(size * 4, size * 4, 1);
        mesh.add(sprite);

        return mesh;
    }

    createGlowTexture(colorHex) {
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 128;
        const ctx = canvas.getContext('2d');
        const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
        const color = new THREE.Color(colorHex);
        gradient.addColorStop(0, `rgba(${color.r * 255}, ${color.g * 255}, ${color.b * 255}, 1)`);
        gradient.addColorStop(0.4, `rgba(${color.r * 255}, ${color.g * 255}, ${color.b * 255}, 0.2)`);
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 128, 128);
        return canvas;
    }

    createCloudTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 256; canvas.height = 256;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'rgba(0,0,0,0)';
        ctx.fillRect(0, 0, 256, 256);

        for (let i = 0; i < 200; i++) {
            const x = Math.random() * 256;
            const y = Math.random() * 256;
            const w = Math.random() * 40 + 10;
            const h = Math.random() * 10 + 5;
            ctx.fillStyle = `rgba(255,255,255, ${Math.random() * 0.5})`;
            ctx.beginPath();
            ctx.ellipse(x, y, w, h, 0, 0, Math.PI * 2);
            ctx.fill();
        }
        return new THREE.CanvasTexture(canvas);
    }

    spawnSpaceship() {
        // Advanced Procedural Ship
        const shipGroup = new THREE.Group();

        // Main Hull
        const hullGeo = new THREE.CylinderGeometry(0.5, 1, 4, 8);
        hullGeo.rotateX(Math.PI / 2);
        const hullMat = new THREE.MeshStandardMaterial({
            color: 0x888888,
            metalness: 0.8,
            roughness: 0.2
        });
        const hull = new THREE.Mesh(hullGeo, hullMat);
        shipGroup.add(hull);

        // Cockpit
        const cockpitGeo = new THREE.BoxGeometry(1.2, 0.8, 1.5);
        const cockpitMat = new THREE.MeshStandardMaterial({ color: 0x222222 });
        const cockpit = new THREE.Mesh(cockpitGeo, cockpitMat);
        cockpit.position.set(0, 0.5, -0.5);
        shipGroup.add(cockpit);

        // Wings (Swept Back)
        const wingShape = new THREE.Shape();
        wingShape.moveTo(0, 0);
        wingShape.lineTo(2, -1);
        wingShape.lineTo(2, 1);
        wingShape.lineTo(0, 2);
        const wingGeo = new THREE.ExtrudeGeometry(wingShape, { depth: 0.2, bevelEnabled: false });
        wingGeo.rotateX(Math.PI / 2);
        const wingMat = new THREE.MeshStandardMaterial({ color: 0xaa0000 });

        const leftWing = new THREE.Mesh(wingGeo, wingMat);
        leftWing.position.set(-1, 0, 0.5);
        leftWing.rotation.z = 0.2;
        shipGroup.add(leftWing);

        const rightWing = new THREE.Mesh(wingGeo, wingMat);
        rightWing.position.set(1, 0, 0.5);
        rightWing.rotation.z = -0.2;
        rightWing.scale.x = -1; // Mirror
        shipGroup.add(rightWing);

        // Engines (Glowing)
        const engineGeo = new THREE.CylinderGeometry(0.4, 0.2, 1, 16);
        engineGeo.rotateX(Math.PI / 2);
        const engineMat = new THREE.MeshBasicMaterial({ color: 0x00ffff });

        const leftEngine = new THREE.Mesh(engineGeo, engineMat);
        leftEngine.position.set(-1.5, 0, 2);
        shipGroup.add(leftEngine);

        const rightEngine = new THREE.Mesh(engineGeo, engineMat);
        rightEngine.position.set(1.5, 0, 2);
        shipGroup.add(rightEngine);

        // Engine Trails
        const trailGeo = new THREE.PlaneGeometry(0.8, 4);
        const trailMat = new THREE.MeshBasicMaterial({
            color: 0x00ffff,
            transparent: true,
            opacity: 0.6,
            side: THREE.DoubleSide
        });

        const leftTrail = new THREE.Mesh(trailGeo, trailMat);
        leftTrail.position.set(-1.5, 0, 4.5);
        leftTrail.rotation.x = Math.PI / 2;
        shipGroup.add(leftTrail);

        const rightTrail = new THREE.Mesh(trailGeo, trailMat);
        rightTrail.position.set(1.5, 0, 4.5);
        rightTrail.rotation.x = Math.PI / 2;
        shipGroup.add(rightTrail);

        // Trajectory
        const startX = (Math.random() > 0.5 ? 1 : -1) * 150;
        const startY = (Math.random() - 0.5) * 80;
        const startZ = (Math.random() - 0.5) * 50;
        const endX = -startX;

        shipGroup.position.set(startX, startY, startZ);
        shipGroup.lookAt(endX, startY, startZ); // Look at destination

        this.scene.add(shipGroup);

        gsap.to(shipGroup.position, {
            x: endX,
            duration: 8 + Math.random() * 4, // Fast
            ease: "none",
            onComplete: () => {
                this.scene.remove(shipGroup);
                // Cleanup
                hullGeo.dispose(); hullMat.dispose();
                wingGeo.dispose(); wingMat.dispose();
                engineGeo.dispose(); engineMat.dispose();
                trailGeo.dispose(); trailMat.dispose();
            }
        });
    }

    createNoiseTexture(type, color) {
        const canvas = document.createElement('canvas');
        canvas.width = 256; canvas.height = 256;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = `rgb(${color.r * 200}, ${color.g * 200}, ${color.b * 200})`;
        ctx.fillRect(0, 0, 256, 256);
        for (let i = 0; i < 3000; i++) {
            const x = Math.random() * 256, y = Math.random() * 256;
            let w = Math.random() * 10, h = Math.random() * 10;
            if (type === 'gas') { w = Math.random() * 200 + 50; h = Math.random() * 5 + 1; }
            else if (type === 'terrestrial') { w = Math.random() * 40 + 10; h = Math.random() * 40 + 10; }
            ctx.fillStyle = `rgba(${color.r * 255}, ${color.g * 255}, ${color.b * 255}, ${Math.random() * 0.3})`;
            ctx.fillRect(x, y, w, h);
        }
        return new THREE.CanvasTexture(canvas);
    }

    setupPostProcessing() {
        const renderScene = new THREE.RenderPass(this.scene, this.camera);
        this.bloomPass = new THREE.UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 1.5, 0.4, 0.85);
        this.bloomPass.threshold = 0.2;
        this.bloomPass.strength = 0.8;
        this.bloomPass.radius = 0.5;

        this.composer = new THREE.EffectComposer(this.renderer);
        this.composer.addPass(renderScene);
        this.composer.addPass(this.bloomPass);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        const delta = this.clock.getDelta(); // Time since last frame
        const time = performance.now() * 0.001;

        // --- Audio Analysis ---
        let targetBass = 0, targetMid = 0, targetTreble = 0;

        if (this.analyser && !this.ufoAudio.paused) {
            this.analyser.getByteFrequencyData(this.dataArray);

            let sumBass = 0; for (let i = 0; i < 10; i++) sumBass += this.dataArray[i];
            targetBass = (sumBass / 10) / 255;

            let sumMid = 0; for (let i = 11; i < 100; i++) sumMid += this.dataArray[i];
            targetMid = (sumMid / 89) / 255;

            let sumTreble = 0; for (let i = 101; i < 255; i++) sumTreble += this.dataArray[i];
            targetTreble = (sumTreble / 154) / 255;
        }

        // Smooth Decay using Delta Time (Frame independent)
        // Smooth Decay using Delta Time (Frame independent)
        // Lower decay = smoother, slower reaction
        const decay = 3.0; // Reduced from 5.0 for smoother transitions
        const factor = 1.0 - Math.exp(-decay * delta);

        this.bass += (targetBass - this.bass) * factor;
        this.mid += (targetMid - this.mid) * factor;
        this.treble += (targetTreble - this.treble) * factor;

        // --- Visual Updates ---

        // 1. Nebula (Vertex Displacement & Color)
        if (this.nebulaMat) {
            this.nebulaMat.uniforms.time.value = time;
            this.nebulaMat.uniforms.uBass.value = this.bass;
            this.nebulaMat.uniforms.uMid.value = this.mid;
            this.nebulaMat.uniforms.uTreble.value = this.treble;
        }

        // 2. Stars
        if (this.starMesh) {
            this.starMesh.rotation.y += (0.0001 + this.mid * 0.001); // Slower rotation
            this.starMesh.scale.setScalar(1.0 + this.bass * 0.3); // Reduced scale impact
        }

        // 3. Camera Shake (Smoother)
        // Always interpolate towards target position (mouse or shake offset)
        let targetX = this.mouse.x * 1.5;
        let targetY = this.mouse.y * 1.5;

        if (this.bass > 0.4) {
            // Smooth shake using sine waves instead of random noise
            const shakeIntensity = (this.bass - 0.4) * 0.5;
            targetX += Math.sin(time * 20.0) * shakeIntensity;
            targetY += Math.cos(time * 15.0) * shakeIntensity;
        }

        // Smoothly interpolate camera to target
        this.camera.position.x += (targetX - this.camera.position.x) * 4.0 * delta;
        this.camera.position.y += (targetY - this.camera.position.y) * 4.0 * delta;

        // 4. Planets & Moons
        this.planets.forEach(p => {
            if (p.userData.speed) {
                p.userData.angle += p.userData.speed;
                const angle = p.userData.angle;
                const x = p.userData.semiMajorAxis * Math.cos(angle);
                const z = p.userData.semiMinorAxis * Math.sin(angle);
                const y = z * Math.sin(p.userData.inclination);
                const zRotated = z * Math.cos(p.userData.inclination);
                p.position.set(x, y, zRotated);
                p.rotation.y += 0.0005; // Very slow planet rotation

                // Animate Moon Pivot if exists
                if (p.userData.moonPivot) {
                    p.userData.moonPivot.rotation.y += p.userData.moonSpeed * 0.5; // Slower moons
                }

                // Animate Clouds if exists
                if (p.userData.clouds) {
                    p.userData.clouds.rotation.y += 0.0008; // Drifting clouds
                }

                if (p.userData.name !== "Subterranean Homesick Alien" && p.userData.name !== "Singularity" && p.userData.name !== "Gargantua" && p.userData.name !== "Einstein-Rosen Bridge") {
                    const scale = 1.0 + this.bass * 0.8;
                    p.scale.setScalar(scale);
                }
            }

            // Animate Black Hole Debris (Independent of Orbit)
            if (p.userData.debris && p.userData.debrisData) {
                const positions = p.userData.debris.geometry.attributes.position.array;
                for (let i = 0; i < p.userData.debrisData.length; i++) {
                    const d = p.userData.debrisData[i];

                    // Gravity Acceleration: The closer they get, the faster they go
                    const gravity = 5.0 / (d.radius * d.radius);
                    d.speed += gravity * 0.01; // Accumulate speed

                    // Spiral In
                    d.angle += d.speed;
                    d.radius -= (0.05 + gravity * 2.0); // Sucking effect increases with gravity

                    // Reset if too close (Event Horizon)
                    if (d.radius < 5.5) {
                        d.radius = 25 + Math.random() * 10;
                        d.angle = Math.random() * Math.PI * 2;
                        d.speed = 0.02 + Math.random() * 0.03; // Reset speed
                    }

                    const x = d.radius * Math.cos(d.angle);
                    const z = d.radius * Math.sin(d.angle);

                    positions[i * 3] = x;
                    positions[i * 3 + 2] = z;
                }
                p.userData.debris.geometry.attributes.position.needsUpdate = true;
            }
        });

        // 5. Bloom
        if (this.bloomPass) {
            this.bloomPass.strength = 0.8 + this.bass * 2.0;
            this.bloomPass.radius = 0.5 + this.mid * 0.5;
        }

        // Raycaster
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(this.planets, true);

        if (intersects.length > 0) {
            let obj = intersects[0].object;
            while (obj.parent && !obj.userData.name) obj = obj.parent;
            if (obj.userData.name) {
                this.onHover(obj.userData.name, obj.position.clone().project(this.camera));
            }
        } else {
            this.onHover(null);
        }

        this.composer.render();
    }

    onResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.composer.setSize(window.innerWidth, window.innerHeight);
    }

    onMouseMove(event) {
        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        // Camera movement is now handled in animate() for shake compatibility
    }

    onClick(event) {
        if (this.audioCtx && this.audioCtx.state === 'suspended') this.audioCtx.resume();

        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(this.planets, true);

        if (intersects.length > 0) {
            let obj = intersects[0].object;
            while (obj.parent && !obj.userData.name) obj = obj.parent;

            if (obj.userData.name === "Subterranean Homesick Alien") {
                this.initAudio();
                if (this.ufoAudio.paused) {
                    this.ufoAudio.play().then(() => {
                        this.showToast("▶ PLAYING: SUBTERRANEAN HOMESICK ALIEN");
                        if (this.achievements) this.achievements.unlock('first_contact');
                    }).catch(console.error);
                    gsap.to(obj.scale, { x: 1.5, y: 1.5, z: 1.5, duration: 0.2, yoyo: true, repeat: 1 });
                } else {
                    this.ufoAudio.pause();
                    this.showToast("⏸ PAUSED");
                }
            }
        }
    }

    showToast(msg) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-10 left-1/2 -translate-x-1/2 bg-retro-card border border-retro-accent text-retro-accent px-6 py-3 rounded-full font-mono text-xs tracking-widest z-50 fade-in-up';
        toast.innerText = msg;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 500);
        }, 3000);
    }

    updateTheme(isLight) {
        gsap.to(this.themeValue, {
            val: isLight ? 1 : 0,
            duration: 1.5,
            ease: "power2.inOut",
            onUpdate: () => { if (this.nebulaMat) this.nebulaMat.uniforms.uTheme.value = this.themeValue.val; }
        });

        if (this.bloomPass) {
            gsap.to(this.bloomPass, { strength: isLight ? 0.0 : 0.6, duration: 1.5 });
        }
    }

    spawnUFO() {
        const ufoGroup = new THREE.Group();
        const hullGeo = new THREE.SphereGeometry(1.5, 32, 16);
        hullGeo.scale(1, 0.3, 1);
        const hullMat = new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.8, roughness: 0.2 });
        const hull = new THREE.Mesh(hullGeo, hullMat);
        ufoGroup.add(hull);

        const cockpitGeo = new THREE.SphereGeometry(0.7, 32, 16);
        const cockpitMat = new THREE.MeshBasicMaterial({ color: 0x00ffff, transparent: true, opacity: 0.8 });
        const cockpit = new THREE.Mesh(cockpitGeo, cockpitMat);
        cockpit.position.y = 0.3;
        ufoGroup.add(cockpit);

        ufoGroup.userData = { name: "Subterranean Homesick Alien" };

        const startX = (Math.random() > 0.5 ? 1 : -1) * 100;
        const startY = (Math.random() - 0.5) * 60;
        const startZ = (Math.random() - 0.5) * 60;
        const endX = -startX;
        const endY = (Math.random() - 0.5) * 60;
        const endZ = (Math.random() - 0.5) * 60;

        ufoGroup.position.set(startX, startY, startZ);
        ufoGroup.lookAt(endX, endY, endZ);
        this.scene.add(ufoGroup);
        this.planets.push(ufoGroup);

        gsap.to(ufoGroup.position, {
            x: endX, y: endY, z: endZ,
            duration: 15, ease: "none",
            onComplete: () => {
                this.scene.remove(ufoGroup);
                const index = this.planets.indexOf(ufoGroup);
                if (index > -1) this.planets.splice(index, 1);
            }
        });

        gsap.to(ufoGroup.rotation, { z: Math.PI * 4, duration: 15, ease: "none" });
    }

    spawnComet() {
        const cometGroup = new THREE.Group();

        // Head
        const headGeo = new THREE.SphereGeometry(0.8, 16, 16);
        const headMat = new THREE.MeshBasicMaterial({ color: 0xaaddff });
        const head = new THREE.Mesh(headGeo, headMat);
        cometGroup.add(head);

        // Glow
        const glowGeo = new THREE.SpriteMaterial({
            map: new THREE.CanvasTexture(this.createGlowTexture('#00ffff')),
            color: 0x00ffff,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending
        });
        const glow = new THREE.Sprite(glowGeo);
        glow.scale.set(8, 8, 1);
        cometGroup.add(glow);

        // Tail (Particles)
        const tailGeo = new THREE.BufferGeometry();
        const tailCount = 50;
        const tailPos = new Float32Array(tailCount * 3);
        const tailSizes = new Float32Array(tailCount);

        for (let i = 0; i < tailCount; i++) {
            tailPos[i * 3] = (Math.random() * 2 + 1) * i * 0.5; // Stretch behind
            tailPos[i * 3 + 1] = (Math.random() - 0.5) * i * 0.1;
            tailPos[i * 3 + 2] = (Math.random() - 0.5) * i * 0.1;
            tailSizes[i] = (1.0 - i / tailCount) * 2.0;
        }
        tailGeo.setAttribute('position', new THREE.BufferAttribute(tailPos, 3));
        tailGeo.setAttribute('size', new THREE.BufferAttribute(tailSizes, 1));

        const tailMat = new THREE.PointsMaterial({
            color: 0x00ffff,
            size: 0.5,
            transparent: true,
            opacity: 0.6,
            blending: THREE.AdditiveBlending
        });
        const tail = new THREE.Points(tailGeo, tailMat);
        tail.rotation.y = Math.PI / 2; // Align with Z axis
        tail.position.x = 1;
        cometGroup.add(tail);

        cometGroup.userData = { name: "Halley's Comet" };

        // Trajectory
        const startX = (Math.random() > 0.5 ? 1 : -1) * 200;
        const startY = (Math.random() - 0.5) * 100;
        const startZ = (Math.random() - 0.5) * 100;
        const endX = -startX;
        const endY = startY + (Math.random() - 0.5) * 50;

        cometGroup.position.set(startX, startY, startZ);
        cometGroup.lookAt(endX, endY, startZ);

        this.scene.add(cometGroup);
        this.planets.push(cometGroup);

        gsap.to(cometGroup.position, {
            x: endX, y: endY,
            duration: 25 + Math.random() * 10, // Much slower comets (25-35s)
            ease: "none",
            onComplete: () => {
                this.scene.remove(cometGroup);
                const idx = this.planets.indexOf(cometGroup);
                if (idx > -1) this.planets.splice(idx, 1);
            }
        });
    }

    createSpaceStation(parentPlanet, size) {
        const stationGroup = new THREE.Group();

        // Core Module
        const coreGeo = new THREE.CylinderGeometry(0.2, 0.2, 1.5, 8);
        const coreMat = new THREE.MeshStandardMaterial({ color: 0xcccccc, metalness: 0.8, roughness: 0.2 });
        const core = new THREE.Mesh(coreGeo, coreMat);
        core.rotation.z = Math.PI / 2;
        stationGroup.add(core);

        // Solar Panels
        const panelGeo = new THREE.BoxGeometry(0.1, 2, 0.5);
        const panelMat = new THREE.MeshStandardMaterial({ color: 0x000044, metalness: 0.5, roughness: 0.1 });

        const leftPanel = new THREE.Mesh(panelGeo, panelMat);
        leftPanel.position.x = -1;
        stationGroup.add(leftPanel);

        const rightPanel = new THREE.Mesh(panelGeo, panelMat);
        rightPanel.position.x = 1;
        stationGroup.add(rightPanel);

        // Ring
        const ringGeo = new THREE.TorusGeometry(0.6, 0.05, 8, 32);
        const ringMat = new THREE.MeshStandardMaterial({ color: 0xeeeeee });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        stationGroup.add(ring);

        // Orbit Logic
        const orbitRadius = size * 2.5;
        stationGroup.position.set(orbitRadius, 0, 0);

        const pivot = new THREE.Group();
        pivot.add(stationGroup);
        parentPlanet.add(pivot);

        // Animate Pivot
        gsap.to(pivot.rotation, { y: Math.PI * 2, duration: 40, repeat: -1, ease: "none" }); // Slower orbit
        // Animate Station Spin
        gsap.to(stationGroup.rotation, { x: Math.PI * 2, duration: 60, repeat: -1, ease: "none" }); // Slower spin

        stationGroup.userData = { name: "ISS Vanguard" };
    }

    createAsteroidBelt() {
        const beltGeo = new THREE.BufferGeometry();
        const count = 2000;
        const posArray = new Float32Array(count * 3);
        const colorArray = new Float32Array(count * 3);

        const color1 = new THREE.Color(0x888888);
        const color2 = new THREE.Color(0x444444);

        for (let i = 0; i < count; i++) {
            const angle = Math.random() * Math.PI * 2;
            const radius = 60 + Math.random() * 20; // Between inner and outer planets
            const spread = (Math.random() - 0.5) * 5; // Vertical spread

            posArray[i * 3] = radius * Math.cos(angle);
            posArray[i * 3 + 1] = spread;
            posArray[i * 3 + 2] = radius * Math.sin(angle);

            const c = Math.random() > 0.5 ? color1 : color2;
            colorArray[i * 3] = c.r;
            colorArray[i * 3 + 1] = c.g;
            colorArray[i * 3 + 2] = c.b;
        }

        beltGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
        beltGeo.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));

        const beltMat = new THREE.PointsMaterial({
            size: 0.4,
            vertexColors: true,
            transparent: true,
            opacity: 0.8
        });

        const belt = new THREE.Points(beltGeo, beltMat);
        belt.userData = { name: "Kuiper Belt" };
        this.scene.add(belt);

        // Rotate the entire belt slowly
        gsap.to(belt.rotation, { y: Math.PI * 2, duration: 480, repeat: -1, ease: "none" }); // Extremely slow belt rotation
    }


    createNyanCatTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 64; canvas.height = 32;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#ffcc99'; ctx.fillRect(20, 8, 32, 20);
        ctx.fillStyle = '#ff99ff'; ctx.fillRect(24, 12, 24, 12);
        ctx.fillStyle = '#ff3399';
        ctx.fillRect(28, 14, 2, 2); ctx.fillRect(36, 18, 2, 2); ctx.fillRect(42, 14, 2, 2);
        ctx.fillStyle = '#999999'; ctx.fillRect(48, 10, 14, 16);
        ctx.fillStyle = '#ffffff'; ctx.fillRect(50, 14, 4, 4); ctx.fillRect(58, 14, 4, 4);
        ctx.fillStyle = '#000000'; ctx.fillRect(52, 16, 2, 2); ctx.fillRect(60, 16, 2, 2);
        ctx.fillStyle = '#999999';
        ctx.fillRect(48, 6, 4, 4); ctx.fillRect(58, 6, 4, 4);
        ctx.fillRect(24, 28, 4, 4); ctx.fillRect(32, 28, 4, 4); ctx.fillRect(44, 28, 4, 4); ctx.fillRect(52, 28, 4, 4);
        ctx.fillStyle = '#999999'; ctx.fillRect(12, 16, 8, 4);
        return new THREE.CanvasTexture(canvas);
    }

    createRainbowTexture() {
        const canvas = document.createElement('canvas');
        canvas.width = 1; canvas.height = 6;
        const ctx = canvas.getContext('2d');
        const colors = ['#ff0000', '#ff9900', '#ffff00', '#33ff00', '#0099ff', '#6633ff'];
        colors.forEach((c, i) => {
            ctx.fillStyle = c;
            ctx.fillRect(0, i, 1, 1);
        });
        return new THREE.CanvasTexture(canvas);
    }

    spawnNyanCat() {
        console.log("🐱 Spawning Nyan Cat...");
        try {
            // Audio
            const audio = new Audio('/static/audio/nyan.mp3');
            audio.volume = 0.5;
            audio.loop = true;
            audio.currentTime = 10; // Start at 10s
            audio.play()
                .then(() => console.log("🎵 Nyan Audio Playing"))
                .catch(e => console.error("⚠️ Audio play failed:", e));

            // Group
            const nyanGroup = new THREE.Group();

            // Cat (Size 4x2)
            console.log("🎨 Creating Cat Texture...");
            const catGeo = new THREE.PlaneGeometry(4, 2);
            const catMat = new THREE.MeshBasicMaterial({ map: this.createNyanCatTexture(), transparent: true, side: THREE.DoubleSide });
            const cat = new THREE.Mesh(catGeo, catMat);
            cat.renderOrder = 1; // Draw on top
            nyanGroup.add(cat);

            // Trail (Size 1.0x1.75) - Anchored to Right
            console.log("🌈 Creating Rainbow Texture...");
            const trailGeo = new THREE.PlaneGeometry(1, 1.75);
            trailGeo.translate(-0.5, 0, 0); // Move origin to right edge
            const trailMat = new THREE.MeshBasicMaterial({ map: this.createRainbowTexture(), side: THREE.DoubleSide });
            const trail = new THREE.Mesh(trailGeo, trailMat);

            // Aggressive Overlap: Attach to center of cat (0.0) and push behind
            trail.position.x = 0.0;
            trail.position.z = -0.1; // Behind cat
            trail.renderOrder = 0; // Draw behind
            trail.scale.x = 0;
            nyanGroup.add(trail);

            // Position
            const yPos = Math.random() * 20 - 10;
            nyanGroup.position.set(-80, yPos, Math.random() * 10 - 5);
            this.scene.add(nyanGroup);
            console.log("🚀 Nyan Cat added to scene at", nyanGroup.position);

            // Animation
            const duration = 8;
            const startTime = Date.now();

            gsap.to(nyanGroup.position, {
                x: 80,
                duration: duration,
                ease: "none",
                onUpdate: () => {
                    const elapsed = (Date.now() - startTime) / 1000;
                    // Random Movement (Sum of Sines)
                    cat.position.y = Math.sin(elapsed * 5) * 1.5 + Math.cos(elapsed * 2) * 1.0;

                    // Trail Logic
                    const distance = nyanGroup.position.x + 80;
                    trail.scale.x = distance;

                    // Trail follows cat vertically
                    trail.position.y = cat.position.y;
                },
                onComplete: () => {
                    console.log("🏁 Nyan Cat finished run");
                    this.scene.remove(nyanGroup);
                    cat.geometry.dispose();
                    cat.material.dispose();
                    trail.geometry.dispose();
                    trail.material.dispose();
                    audio.pause();
                }
            });
        } catch (error) {
            console.error("🔥 Error spawning Nyan Cat:", error);
        }
    }
}
