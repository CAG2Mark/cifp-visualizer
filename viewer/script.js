import * as THREE from 'three';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js'
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js'

var TO_RAD = Math.PI / 180;
var EARTH_RADIUS = 3443.9184665;

var camera, scene, renderer;
var lat = -14, lon = -73;
var latR = TO_RAD * lat;
var lonR = TO_RAD * lon;
var UPDOWN_BOUND = 87 * TO_RAD;

let up;

function updateLatLonRad(newLat, newLon) {
    lat = newLat / TO_RAD;
    lon = newLon / TO_RAD;
    latR = newLat;
    lonR = newLon;
    updateUp();
}

function updateUp() {
    up = new THREE.Vector3(
        Math.cos(latR) * Math.cos(lonR),
        Math.sin(latR),
        -Math.cos(latR) * Math.sin(lonR)
    );
}
updateUp();

let UP_shifted = new THREE.Vector3(
    Math.cos(latR + 0.1) * Math.cos(lonR + 0.1),
    Math.sin(latR + 0.1),
    -Math.cos(latR + 0.1) * Math.sin(lonR + 0.1)
);

// http://localhost:8080/proc/SPZO/approach/R28/SDARK/28/20A.obj

let airport = "SPZO"
let kind = "approach"
let ident = "R28"
let trans = "SDARK"
let rwy = "28"


async function loadApproach(airport, kind, ident, trans, rwy) {
    let prefix = `../proc/${airport}/${kind}/${ident}/${trans}/${rwy}`
    let data = await (await fetch(prefix)).json()
    
    let promises = []
    for (let i = 0; i < data.length; ++i) {
        let leg = data[i]
        promises.push(load_obj(`${prefix}/${leg["legId"]}.obj`))
    }
    await Promise.all(promises)
}

async function do_debug() {
    let lat = -14;
    let lon = -73;
    loadApproach(airport, kind, ident, trans, rwy)
    // await load_obj("../proc/SPZO/approach/R28/SDARK/28/R20.obj")
    // await load_obj("../proc/SPZO/approach/R28/SDARK/28/R22.obj")
    // let a = load_tile(lat, lon, 13);
    // let b = load_tile(lat, lon + 1, 13);
    //let c = load_tile(lat + 1, lon, 13);
    //let d = load_tile(lat + 1, lon + 1, 13);
    //Promise.all([a, b, c, d]);

    go_to_tile(lat, lon)
    submit_icao("VHHH")
}

let NEGUP = new THREE.Vector3(up.x, up.y, up.z).negate();

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
    var latR = TO_RAD * lat;
    var lonR = TO_RAD * lon;
    
    let up = new THREE.Vector3(
        Math.cos(latR) * Math.cos(lonR),
        Math.sin(latR),
        -Math.cos(latR) * Math.sin(lonR)
    );
    
    let pos = new THREE.Vector3(up.x, up.y, up.z);
    pos.multiplyScalar(3447);

    camera.position.x = pos.x;
    camera.position.y = pos.y;
    camera.position.z = pos.z;

    camera.up = up;

    cameraHdg = 0; // north
    cameraUpDown = 0;

    // look straight north
    // right hand rule
    let north = new THREE.Vector3(
        Math.cos(latR) * Math.sin(lonR),
        0,
        Math.cos(latR) * Math.cos(lonR),
    ).cross(up).add(camera.position);

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
                    var texture = new THREE.TextureLoader().load(photo);

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


do_debug()

function init() {

    camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;

    scene = new THREE.Scene();

    let light = new THREE.DirectionalLight(0xffffff);
    light.position.set(UP_shifted.x, UP_shifted.y, UP_shifted.z);
    scene.add(light);

    renderer = new THREE.WebGLRenderer();

    renderer.setClearColor(0x86cdfa);

    let renderArea = document.getElementById("render-area");

    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderArea.appendChild(renderer.domElement);

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
    let box = document.getElementById("render-area").getBoundingClientRect();
    
    camera.aspect = box.width / box.height;
    camera.updateProjectionMatrix();

    renderer.setSize(box.width, box.height);

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
    let c = new THREE.Vector3(up.x, up.y, up.z);
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
    
    let cameraPos = new THREE.Vector3();
    cameraPos.copy(camera.position);
    
    let norm = Math.sqrt(cameraPos.dot(cameraPos));
    
    let newLat = Math.asin(cameraPos.y / norm);
    let newLon = -Math.atan2(cameraPos.z, cameraPos.x);
    
    updateLatLonRad(newLat, newLon);
    camera.up = up;

    if (isMouseDown) {
        // create an orthonormal frame

        let east = new THREE.Vector3(
            -Math.cos(latR) * Math.sin(lonR),
            0,
            -Math.cos(latR) * Math.cos(lonR),
        ).normalize();

        let north = new THREE.Vector3();
        north.crossVectors(up, east);

        let eastCopy = new THREE.Vector3();
        eastCopy.copy(east);
        eastCopy.multiplyScalar(-Math.sin(cameraHdg))

        let forward = new THREE.Vector3();
        forward.copy(north).multiplyScalar(Math.cos(cameraHdg)).add(eastCopy);

        // combine with up/down angle
        let upCopy = new THREE.Vector3(
            up.x, up.y, up.z
        ).multiplyScalar(Math.sin(cameraUpDown));

        // combine with up/down angle
        forward
            .multiplyScalar(Math.cos(cameraUpDown))
            .add(upCopy)

        forward.add(camera.position);

        camera.lookAt(forward);
    }

    renderer.render(scene, camera);
}

var icaoBtn = document.getElementById("submit-airport-button");
var icaoInput = document.getElementById("airport-input")
icaoBtn.addEventListener("click", on_icao_submit);

var procTemplate = document.getElementById("proc-container-template");
procTemplate.attributes.removeNamedItem("id");

document.getElementById("templates").remove();

var sidsArea = document.getElementById("sidebar-sid-area");
var starArea = document.getElementById("sidebar-star-area");
var appchArea = document.getElementById("sidebar-approach-area");

function populateChild(node, name, value) {
    node.getElementsByClassName(name)[0].textContent = value;
}

function rwy_str(data) {
    if (data["isAllRwys"]) {
        return "All Runways";
    }
    if (data.hasOwnProperty("runway")) {
        if (data["runway"]) {
            return "RW" + data["runway"];
        }
        return "Circle to Land";
    }
    let str = "RW";
    let rwys = data["runways"];
    for (let i = 0; i < rwys.length; ++i) {
        if (i > 0) str += ", ";
        str += rwys[i];
    }
    return str;
}

function firstRwy(data) {
    if (data.hasOwnProperty("runway") && data["runway"]) {
        if (data["runway"]) {
            return "RW" + data["runway"];
        } else {
            return "none"
        }
    }
    
    let rwys = data["runways"];
    if (rwys.length > 0) return rwys[0];
    return "none";
}

var curProc;
var curAirport;
var curRwy;
var curTrans;

async function loadProc(proc) {
    curTrans = "none";
    curRwy = firstRwy(proc);
    
    curProc = proc;
    let airport = curAirport;
    let kind = proc["kind"];
    let ident = proc["id"];
    let trans = curTrans;
    let rwy = curRwy;
    let data = await (await fetch(`../proc/${airport}/${kind}/${ident}/${trans}/${rwy}`)).json()
    console.log(data);
}

function registerProcClickListener(node, proc) {
    node.addEventListener("click", () => loadProc(proc));
}

function populateAirportData(data) {
    sidsArea.replaceChildren([]);
    starArea.replaceChildren([]);
    appchArea.replaceChildren([]);
    
    let sids = data["sids"];
    for (let i = 0; i < sids.length; ++i) {
        let proc = sids[i];
        let node = procTemplate.cloneNode(true);
        populateChild(node, "proc-header", proc["id"]);
        populateChild(node, "proc-rwys", rwy_str(proc));
        registerProcClickListener(node, proc);
        sidsArea.appendChild(node);
    }
    
    let stars = data["stars"];
    for (let i = 0; i < stars.length; ++i) {
        let proc = stars[i];
        let node = procTemplate.cloneNode(true);
        populateChild(node, "proc-header", proc["id"]);
        populateChild(node, "proc-rwys", rwy_str(proc));
        registerProcClickListener(node, proc);
        starArea.appendChild(node);
    }
    
    let appches = data["approaches"];
    for (let i = 0; i < appches.length; ++i) {
        let proc = appches[i];
        let node = procTemplate.cloneNode(true);
        populateChild(node, "proc-header", proc["id"]);
        populateChild(node, "proc-rwys", rwy_str(proc));
        registerProcClickListener(node, proc);
        appchArea.appendChild(node);
    }
}

let submitLock = false;

async function submit_icao(val) {
    curAirport = val;
    
    val = val.trim().toUpperCase();
    let res = await fetch("../airport/" + val);
    if (res.status == 404) {
        alert("Airport " + val + " not found.");
        submitLock = false;
        return;
    }
    let data = await res.json();
    populateAirportData(data);
    submitLock = false;
}

async function on_icao_submit() {
    if (submitLock) return;
    submitLock = true;
    let val = icaoInput.value.toUpperCase();
    await submit_icao(val);
}

icaoInput.addEventListener("keyup", e => {
    if (!submitLock && e.key == "Enter") {
        on_icao_submit();
    }
})
