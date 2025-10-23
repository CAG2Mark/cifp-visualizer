import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js'
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js'

var TO_RAD = Math.PI / 180;

var controls;
var camera, scene, renderer;
var mesh;
var lat = 47, lon = 11;
var latR = TO_RAD * lat;
var lonR = TO_RAD * lon;
var UPDOWN_BOUND = 87 * TO_RAD;

let UP = new THREE.Vector3(
    Math.cos(latR) * Math.cos(lonR),
    Math.sin(latR),
    -Math.cos(latR) * Math.sin(lonR)
);

let NEGUP = new THREE.Vector3(UP.x, UP.y, UP.z).negate();

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ensure_url("../photo/22/113/13.jpg");
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
                `../terrain/${lat}/${lon}/0.obj`,
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

let cameraHdg = 0; // initially north
let cameraUpDown = 0; // initially level with the ground

let last_update;

init();
last_update = window.performance.now();
animate();

let a = load_tile(lat, lon, 14);
// let b = load_tile(lat, lon + 1, 13);
// let c = load_tile(lat, lon + 2, 13);
Promise.all([a, b, c]);

function init() {

    camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;

    scene = new THREE.Scene();

    let light = new THREE.DirectionalLight(0xffffff);
    light.position.set(UP.x, UP.y, UP.z);
    scene.add(light);

    renderer = new THREE.WebGLRenderer();
    
    if (false) {
        // add a ground plane
        var geometry = new THREE.PlaneGeometry( 1000, 1000 );
        var material = new THREE.MeshPhongMaterial( {color: 0xffff00, side: THREE.DoubleSide} );
        var plane = new THREE.Mesh( geometry, material );
        plane.rotation.x = 90 * Math.PI / 180;
        plane.position.y = -100.01;
        scene.add( plane );
    }

    // set the background color to gray
    renderer.setClearColor(0xa0a0a0);

    let renderArea = document.getElementById("render-area");

    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderArea.appendChild(renderer.domElement);

    // let's have the mouse affect the view
    // controls = new PointerLockControls(camera, renderer.domElement);

    //

    window.addEventListener('resize', onWindowResize, false);

    // window.addEventListener('click', () => controls.lock());
    renderArea.addEventListener('mousedown', (e) => { 
        mouseFirst = true; isMouseDown = true;
    });
    
    renderArea.addEventListener('contextmenu', (e) => {
        e.preventDefault();
    })
    
    renderArea.addEventListener('mouseup', () => isMouseDown = false);
    renderArea.addEventListener('mouseleave', () => isMouseDown = false);
    renderArea.addEventListener('mousemove', (e) => { mouseX = e.clientX; mouseY = e.clientY; })

    // scene.add(controls.object);

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
    // auto-rotation at start - turn it off
    //mesh.rotation.x += 0.005;
    //mesh.rotation.y += 0.01;
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
            
            cameraHdg -= xDel / 15 * TO_RAD * timeFactor;
            cameraUpDown -= yDel / 15 * TO_RAD * timeFactor;
            
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
    // console.log(camera.up);
    
    if (isMouseDown) {
        // vector looking straight forward, combined with heading
        let forward = new THREE.Vector3(
            Math.cos(latR) * Math.sin(lonR + cameraHdg),
            0,
            Math.cos(latR) * Math.cos(lonR + cameraHdg),
        ).cross(UP);
        
        // combine with up/down angle
        let upCopy = new THREE.Vector3(
            UP.x, UP.y, UP.z
        ).multiplyScalar(Math.sin(cameraUpDown));
        
        console.log(cameraUpDown);
        // combine with up/down angle
        forward
            .multiplyScalar(Math.cos(cameraUpDown))
            .add(upCopy)
            
        forward.add(camera.position);

        camera.lookAt(forward);
    }
    

    // controls.moveForward(velA);
    // controls.moveRight(velB);
    
    renderer.render(scene, camera);
    // have the mouse update the view
    // controls.update();

    // console.log(camera.position)
}
