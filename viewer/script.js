import * as THREE from 'three';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js'
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js'

var TO_RAD = Math.PI / 180;

var camera, scene, renderer;
var lat = 59, lon = -2;
var latR = TO_RAD * lat;
var lonR = TO_RAD * lon;
var UPDOWN_BOUND = 87 * TO_RAD;

let UP = new THREE.Vector3(
    Math.cos(latR) * Math.cos(lonR),
    Math.sin(latR),
    -Math.cos(latR) * Math.sin(lonR)
);

let UP_shifted = new THREE.Vector3(
    Math.cos(latR+0.1) * Math.cos(lonR+0.1),
    Math.sin(latR+0.1),
    -Math.cos(latR+0.1) * Math.sin(lonR+0.1)
);


let NEGUP = new THREE.Vector3(UP.x, UP.y, UP.z).negate();

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function ensure_url(url) {
    while (true) {
        let res = await fetch(url);
        if (res.status == 202) {
            console.log(await res.text());
            await sleep(200);
        } else {
            await res.blob();
            return;
        }
    }
}

async function load_obj(file) {
    console.log("loading " + file)
    const loader = new OBJLoader();
    loader.load(
        file,
        function (object) {
            scene.add(object);
        },
        (xhr) => {
            console.log((xhr.loaded / xhr.total) * 100 + '% loaded')
        },
        (error) => {
            console.log(error)
        }
    )
}

function go_to_tile(lat, lon) {
    let pos = new THREE.Vector3(UP.x, UP.y, UP.z);
    pos.multiplyScalar(3447);

    camera.position.x = pos.x;
    camera.position.y = pos.y;
    camera.position.z = pos.z;

    camera.up = UP;

    cameraHdg = 0; // north
    cameraUpDown = 0;

    // look straight north
    // right hand rule
    let north = new THREE.Vector3(
        Math.cos(latR) * Math.sin(lonR),
        0,
        Math.cos(latR) * Math.cos(lonR),
    ).cross(UP).add(camera.position);

    camera.lookAt(north);
}

async function load_tile(lat, lon, zl) {
    // ensure the things that need loading
    // photo URL
    let photo = `../photo/${lat}/${lon}/${zl}.jpg`;
    let terr = `../terrain/${lat}/${lon}/0.obj`;

    let a = ensure_url(photo);
    let b = ensure_url(terr);

    await Promise.all([a, b]);

    console.log("awaited");

    let mtl = new MTLLoader();
    mtl.load(
        'terrain.mtl',
        function (materials) {
            materials.preload();
            const loader = new OBJLoader();
            loader.setMaterials(materials);
            loader.load(
                terr,
                function (object) {
                    var texture = new THREE.TextureLoader().load(`../photo/${lat}/${lon}/${zl}.jpg`);

                    object.traverse(function (child) {   // aka setTexture
                        if (child instanceof THREE.Mesh) {
                            child.material.map = texture;
                        }
                    });
                    scene.add(object);
                },
                (xhr) => {
                    console.log((xhr.loaded / xhr.total) * 100 + '% loaded')
                },
                (error) => {
                    console.log(error)
                }
            )
        }
    )
    go_to_tile(lat, lon)
}

let moveForward = false;
let moveBackward = false;
let moveLeft = false;
let moveRight = false;
let moveUp = false;
let moveDown = false;
let fast = false;
let isMouseDown = false;
let mouseX = 0;
let mouseY = 0;
let mouseXOld = 0;
let mouseYOld = 0;
let mouseFirst = false;
let touching = false;

let cameraHdg = 0; // initially north
let cameraUpDown = 0; // initially level with the ground

let last_update;

init();
last_update = window.performance.now();
animate();


// let a = load_tile(lat, lon, 13);
// let b = load_tile(lat + 1, lon, 13);
//let c = load_tile(lat + 1, lon, 13);
//let d = load_tile(lat + 1, lon + 1, 13);
//Promise.all([a, b, c, d]);

go_to_tile(lat, lon)

// await load_obj("EGPB_D27_D355L_A_10.obj");
// await load_obj("EGPB_D27_D355L_A_20.obj");
// await load_obj("EGPB_D27_D355L_A_30.obj");
await load_obj("EGPB_D27_D355L_A_40.obj");
// await load_obj("EGPB_D27_D355L_A_40_good.obj");
// await load_obj("EGPB_D27_D355L_D_20.obj");
// await load_obj("EGPB_D27_D355L_D_30.obj");

function init() {

    camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;

    scene = new THREE.Scene();

    let light = new THREE.DirectionalLight(0xffffff);
    light.position.set(UP_shifted.x, UP_shifted.y, UP_shifted.z);
    scene.add(light);

    renderer = new THREE.WebGLRenderer();

    // set the background color to gray
    renderer.setClearColor(0xa0a0a0);

    let renderArea = document.getElementById("render-area");

    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderArea.appendChild(renderer.domElement);

    //

    window.addEventListener('resize', onWindowResize, false);
    renderer.domElement.addEventListener('mousedown', (e) => {
        mouseFirst = true; isMouseDown = true;
        e.preventDefault();
    });

    renderer.domElement.addEventListener('contextmenu', (e) => {
        e.preventDefault();
    })

    renderer.domElement.addEventListener('mouseup', () => isMouseDown = false);
    renderer.domElement.addEventListener('mouseleave', () => isMouseDown = false);
    renderer.domElement.addEventListener('mousemove', (e) => { if (!touching) { mouseX = e.clientX; mouseY = e.clientY; } })

    renderer.domElement.addEventListener('touchstart', (e) => {
        mouseFirst = true; isMouseDown = true; touching = true;
        mouseX = -e.touches[0].clientX;
        mouseY = -e.touches[0].clientY;
    });

    renderer.domElement.addEventListener('touchmove', (e) => { mouseX = -e.touches[0].clientX; mouseY = -e.touches[0].clientY; })
    renderer.domElement.addEventListener('touchend', () => { isMouseDown = false; touching = false; });
    renderer.domElement.addEventListener('touchcancel', () => { isMouseDown = false; touching = false; });

    const onKeyDown = function (event) {
        switch (event.code) {
            case 'ArrowUp':
            case 'KeyW':
                moveForward = true;
                break;
            case 'ArrowLeft':
            case 'KeyA':
                moveLeft = true;
                break;
            case 'ArrowDown':
            case 'KeyS':
                moveBackward = true;
                break;
            case 'ArrowRight':
            case 'KeyD':
                moveRight = true;
                break;
            case 'KeyQ':
                moveDown = true;
                break;
            case 'KeyE':
                moveUp = true;
                break;
            case 'ShiftLeft':
                fast = true;
                break;
        }
    };

    const onKeyUp = function (event) {
        switch (event.code) {
            case 'ArrowUp':
            case 'KeyW':
                moveForward = false;
                break;
            case 'ArrowLeft':
            case 'KeyA':
                moveLeft = false;
                break;
            case 'ArrowDown':
            case 'KeyS':
                moveBackward = false;
                break;
            case 'ArrowRight':
            case 'KeyD':
                moveRight = false;
                break;
            case 'KeyQ':
                moveDown = false;
                break;
            case 'KeyE':
                moveUp = false;
                break;
            case 'ShiftLeft':
                fast = false;
                break;
        }
    };

    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('keyup', onKeyUp);


}

function onWindowResize() {

    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize(window.innerWidth, window.innerHeight);

}

function animate() {

    requestAnimationFrame(animate);
    let vel = 0.025;

    let tmp = window.performance.now();
    let timeFactor = 0.1 * (tmp - last_update);
    last_update = tmp;

    if (fast) vel = 0.15;

    let velA = 0, velB = 0, velC = 0;

    if (moveForward) {
        velA += vel;
    } else if (moveBackward) {
        velA += -vel;
    }

    if (moveRight) {
        velB += vel;
    } else if (moveLeft) {
        velB += -vel;
    }

    if (moveUp) {
        velC += vel;
    } else if (moveDown) {
        velC += -vel;
    }

    if (isMouseDown) {
        if (mouseFirst) {
            mouseFirst = false;
        } else {
            let xDel = mouseX - mouseXOld;
            let yDel = mouseY - mouseYOld;

            cameraHdg -= xDel / 7 * TO_RAD * timeFactor;
            cameraUpDown -= yDel / 7 * TO_RAD * timeFactor;

            cameraUpDown = Math.max(Math.min(cameraUpDown, UPDOWN_BOUND), -UPDOWN_BOUND);
        }
        mouseXOld = mouseX;
        mouseYOld = mouseY;
    }

    let a = new THREE.Vector3();
    camera.getWorldDirection(a);
    let c = new THREE.Vector3(UP.x, UP.y, UP.z)
    let b = new THREE.Vector3();
    b.crossVectors(a, c).normalize();

    a.crossVectors(c, b);

    a.multiplyScalar(velA);
    b.multiplyScalar(velB);
    c.multiplyScalar(velC);
    a.add(b);
    a.add(c);

    a.multiplyScalar(timeFactor);

    camera.position.add(a);

    if (isMouseDown) {
        // create an orthonormal frame

        let east = new THREE.Vector3(
            -Math.cos(latR) * Math.sin(lonR),
            0,
            -Math.cos(latR) * Math.cos(lonR),
        ).normalize();

        let north = new THREE.Vector3();
        north.crossVectors(UP, east);

        let eastCopy = new THREE.Vector3();
        eastCopy.copy(east);
        eastCopy.multiplyScalar(-Math.sin(cameraHdg))

        let forward = new THREE.Vector3();
        forward.copy(north).multiplyScalar(Math.cos(cameraHdg)).add(eastCopy);

        // combine with up/down angle
        let upCopy = new THREE.Vector3(
            UP.x, UP.y, UP.z
        ).multiplyScalar(Math.sin(cameraUpDown));

        // combine with up/down angle
        forward
            .multiplyScalar(Math.cos(cameraUpDown))
            .add(upCopy)

        console.log(cameraHdg, cameraUpDown);

        forward.add(camera.position);

        camera.lookAt(forward);
    }

    renderer.render(scene, camera);
}
