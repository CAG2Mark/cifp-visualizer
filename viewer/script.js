import * as THREE from 'three';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js'
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js'

function $(val) {
    return document.getElementById(val);
}

const TO_RAD = Math.PI / 180;
const EARTH_RADIUS = 3443.9184665;
const NM_TO_FT = 6076.12

var camera, scene, renderer;
var lat = 0, lon = 0;
var latR = TO_RAD * lat;
var lonR = TO_RAD * lon;
var UPDOWN_BOUND = 87 * TO_RAD;

var up;
var upShifted = new THREE.Vector3(
    Math.cos(latR + 0.1) * Math.cos(lonR + 0.1),
    Math.sin(latR + 0.1),
    -Math.cos(latR + 0.1) * Math.sin(lonR + 0.1)
);

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
    upShifted = new THREE.Vector3(
        Math.cos(latR + 0.1) * Math.cos(lonR + 0.1),
        Math.sin(latR + 0.1),
        -Math.cos(latR + 0.1) * Math.sin(lonR + 0.1)
    );
}
updateUp();



// http://localhost:8080/proc/SPZO/approach/R28/SDARK/28/20A.obj

let airport = "SPZO"
let kind = "approach"
let ident = "R28"
let trans = "SDARK"
let rwy = "28"




async function do_debug() {
    let lat = 27;
    let lon = 88;
    // await load_obj("../proc/SPZO/approach/R28/SDARK/28/R20.obj")
    // await load_obj("../proc/SPZO/approach/R28/SDARK/28/R22.obj")
    // let a = loadTile(lat, lon, 13);
    // let b = loadTile(lat, lon + 1, 13);
    //let c = load_tile(lat + 1, lon, 13);
    //let d = load_tile(lat + 1, lon + 1, 13);
    //Promise.all([a, b, c, d]);

    // go_to_pos(lat, lon, 0)
    // submit_icao("VHHH")
}

function loadObj(id, file, mtlFile) {
    console.log("loading " + file)

    return new Promise((resolve, reject) => {
        let mtl = new MTLLoader();
        mtl.load(
            mtlFile,
            function (materials) {
                materials.preload();
                const loader = new OBJLoader();
                loader.setMaterials(materials);
                loader.load(
                    file,
                    function (object) {
                        scene.add(object);
                        resolve([id, object]);
                    },
                    (xhr) => {
                        console.log((xhr.loaded / xhr.total) * 100 + '% loaded');
                    },
                    (error) => {
                        console.log(error);
                        reject(error);
                    }
                )
            }
        )
    })

}

function go_to_pos(lat, lon, altitude) {
    updateLatLonRad(lat * TO_RAD, lon * TO_RAD);
    scene.remove(light);
    light = new THREE.DirectionalLight(0xaaaaaa);
    light.position.set(upShifted.x, upShifted.y, upShifted.z);
    scene.add(light);

    let pos = new THREE.Vector3(up.x, up.y, up.z);
    pos.multiplyScalar(EARTH_RADIUS + altitude / NM_TO_FT);

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

var light;

function init() {

    camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;

    scene = new THREE.Scene();

    light = new THREE.DirectionalLight(0xffffff);
    light.position.set(upShifted.x, upShifted.y, upShifted.z);
    scene.add(light);
    
    let ambient = new THREE.AmbientLight( 0xffffff );
    scene.add(ambient);

    renderer = new THREE.WebGLRenderer();

    renderer.setClearColor(0x86cdfa);
    
    renderer.domElement.tabIndex = 1;

    let renderArea = $("render-area");

    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderArea.appendChild(renderer.domElement);
    
    onWindowResize();

    window.addEventListener('resize', onWindowResize, false);
    renderer.domElement.addEventListener('mousedown', (e) => {
        window.focus();
        if (document.activeElement) {
            document.activeElement.blur();
        }
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
        if (event.code == "Escape") {
            hidePopups();
            return;
        }
        
        if (document.activeElement != document.body) return;
        
        switch (event.code) {
            case 'ArrowLeft':
                if (selectedLeg && legListeners[selectedLeg]) {
                    legListeners[selectedLeg](false);
                }
                break;
            case 'ArrowRight':
                if (selectedLeg && legListeners[selectedLeg]) {
                    legListeners[selectedLeg](true);
                }
                break;
            case 'KeyW':
                moveForward = true;
                break;
            case 'KeyA':
                moveLeft = true;
                break;
            case 'KeyS':
                moveBackward = true;
                break;
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
            case 'KeyW':
                moveForward = false;
                break;
            case 'KeyA':
                moveLeft = false;
                break;
            case 'KeyS':
                moveBackward = false;
                break;
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
    let vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    let vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);

    camera.aspect = Math.max(0, (vw - 350) / (vh));
    camera.updateProjectionMatrix();

    renderer.setSize(Math.max(0, vw - 350), vh);

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

            cameraHdg -= xDel / 7 * TO_RAD;
            cameraUpDown -= yDel / 7 * TO_RAD;

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

var icaoBtn = $("submit-airport-button");
var icaoInput = $("airport-input")
icaoBtn.addEventListener("click", on_icao_submit);

var procTemplate = $("proc-container-template");
procTemplate.attributes.removeNamedItem("id");

var legTemplate = $("leg-container-template");
legTemplate.attributes.removeNamedItem("id");

var missedApp = $("legs-missed-approach");
missedApp.attributes.removeNamedItem("id");

var jobTemplate = $("job-container-template");
jobTemplate.attributes.removeNamedItem("id");

$("templates").remove();

var sidsArea = $("sidebar-sid-area");
var starArea = $("sidebar-star-area");
var appchArea = $("sidebar-approach-area");

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
    if (data.hasOwnProperty("runway")) {
        if (data["runway"]) {
            return data["runway"];
        } else {
            return "none"
        }
    }

    let rwys = data["runways"];
    if (rwys.length > 0) return rwys[0];
    return "none";
}

function rwyAsList(data) {
    if (data.hasOwnProperty("runway")) {
        if (data["runway"]) return [data["runway"]];
        return [];
    }
    return data["runways"];
}

var prevAirport;

var curProc;
var curAirport;
var curRwy;
var curTrans;
var curObjs = {};

let legsAirport = $("legs-airport");
let legsKind = $("legs-kind");
let legsIdent = $("legs-ident");

function procKind(data) {
    switch (data["kind"]) {
        case "sid": return "SID";
        case "star": return "STAR";
        case "approach": return "APP";
        default: return ""
    }
}

let airportSidebarArea = $("sidebar-airport-area");
let legsSidebarArea = $("sidebar-legs-area");
let rwySel = $("runway-selection");
let transSel = $("transition-selection");

let initingProc = false;
async function initProc(proc) {
    initingProc = true;
    curTrans = "none";
    curRwy = firstRwy(proc);

    curProc = proc;

    legsAirport.textContent = curAirport;
    legsKind.textContent = procKind(proc);
    legsIdent.textContent = proc["id"];

    rwySel.replaceChildren([]);
    transSel.replaceChildren([]);

    let rwys = rwyAsList(proc);
    let transitions = proc["transitions"];

    if (rwys.length == 0) {
        let opt = document.createElement("option");
        opt.textContent = "No Runway";
        opt.value = "none";
        opt.selected = true;
        rwySel.appendChild(opt);
    }
    else {
        for (let i = 0; i < rwys.length; ++i) {
            let elem = rwys[i];
            let opt = document.createElement("option");
            opt.textContent = "Runway " + elem;
            opt.value = elem;
            if (elem == curRwy) opt.selected = true;
            rwySel.appendChild(opt);
        }
    }

    let opt = document.createElement("option");
    opt.textContent = "No Transition";
    opt.value = "none";
    opt.selected = true;
    transSel.appendChild(opt);

    transSel.appendChild(opt);
    for (let i = 0; i < transitions.length; ++i) {
        let elem = transitions[i];
        let opt = document.createElement("option");
        opt.textContent = elem;
        opt.value = elem;
        transSel.appendChild(opt);
    }

    initingProc = false;

    airportSidebarArea.classList.add("hidden");
    legsSidebarArea.classList.remove("hidden");

    await loadProc();
}


var selectedObj = null;
var selectedLeg = null;
var legRadios = {};
var prevR;
var prevG;
var prevB;
var prevOpacity;

function unselectObj() {
    selectedObj.traverse(function (child) {
        if (child instanceof THREE.Mesh) {
            child.material.color.r = prevR;
            child.material.color.g = prevG;
            child.material.color.b = prevB;
            child.material.opacity = prevOpacity;
        }
    });
}

function selLeg(legId) {
    if (selectedObj) {
        unselectObj(selectedObj);
    }
    selectObj(curObjs[legId]);
    legRadios[legId].checked = true;
    selectedObj = curObjs[legId];
    selectedLeg = legId;
}

function selectObj(object) {
    object.traverse(function (child) {
        if (child instanceof THREE.Mesh) {
            console.dir(child.material);
            prevR = child.material.color.r;
            prevG = child.material.color.g;
            prevB = child.material.color.b;
            prevOpacity = child.material.opacity;
            child.material.color.r = 1;
            child.material.color.g = 0.1;
            child.material.color.b = 0.1;
            child.material.opacity = 1;
        }
    });
}

function registerLegClickListener(node, legId) {
    node.addEventListener("click", () => {
        selLeg(legId);
    })
}

let legListeners = {};

function registerLegKeyListeners(legId, prevLeg, nextLeg) {
    legListeners[legId] = goNext => {
        if (goNext && nextLeg) selLeg(nextLeg);
        else if (!goNext && prevLeg) selLeg(prevLeg);
    }
}

let legsArea = $("legs-area");
let loadingProc = false;
async function loadProc() {
    if (initingProc) return;
    if (loadingProc) return;
    
    let updatePos = curAirport != prevAirport;
    prevAirport = curAirport;

    let objs = Object.values(curObjs);
    for (let i = 0; i < objs.length; ++i) {
        scene.remove(objs[i]);
    }

    rwySel.disabled = true;
    transSel.disabled = true;

    loadingProc = true;

    let proc = curProc;
    let airport = curAirport;
    let kind = proc["kind"];
    let ident = proc["id"];
    let trans = curTrans;
    let rwy = curRwy;

    let prefix = `../proc/${airport}/${kind}/${ident}/${trans}/${rwy}`;
    let data = await (await fetch(prefix)).json()

    legsArea.replaceChildren([]);

    let promises = [];
    
    let isMap = false;
    
    legListeners = {};
    legRadios = {};

    for (let i = 0; i < data.length; ++i) {
        let leg = data[i];
        let id = "leg-item-" + leg["legId"]
        let node = legTemplate.cloneNode(true);

        if (leg["fmap"]) {
            isMap = true;
            legsArea.appendChild(missedApp.cloneNode(true));
        }

        let radio = node.getElementsByClassName("leg-radio")[0];
        radio.id = id;
        
        legRadios[leg["legId"]] = radio;

        let lbl = node.getElementsByClassName("leg-label")[0];
        lbl.setAttribute("for", id);

        let alt = leg["altitude"] ? leg["altitude"] : "";
        let spd = leg["speed"] ? leg["speed"] : "";
        let sep = alt && spd ? ", " : "";

        populateChild(node, "leg-type", leg["kind"]);
        populateChild(node, "leg-fix", leg["fix"]);
        populateChild(node, "leg-restr", (alt + sep + spd).trimStart());

        legsArea.appendChild(node);
        registerLegClickListener(lbl, leg["legId"]);
        
        let prevLeg = null, nextLeg = null;
        if (i != 0) prevLeg = data[i - 1]["legId"];
        if (i != data.length - 1) nextLeg = data[i + 1]["legId"];
        registerLegKeyListeners(leg["legId"], prevLeg, nextLeg);
        
        let mtl = isMap ? "mappath.mtl" : "path.mtl"; 
        promises.push(loadObj(leg["legId"], prefix + "/" + leg["legId"] + ".obj", mtl));
    }

    let points = await (await fetch(prefix + "/points.json")).json();
    let latlon = points["initialLatLon"];
    let alt = points["initialAlt"];

    if (updatePos) {
        go_to_pos(latlon[0] - 0.1, latlon[1], alt + 4000);
    }

    let vals = await Promise.all(promises);
    curObjs = {};
    for (let i = 0; i < vals.length; ++i) {
        let [id, obj] = vals[i];
        curObjs[id] = obj;
    }

    rwySel.disabled = false;
    transSel.disabled = false;

    loadingProc = false;

    let tiles = await (await fetch(prefix + "/tiles.json")).json();
    let tilesDict = {};
    
    for (let i = 0; i < tiles.length; ++i) {
        let tile = tiles[i]
        tilesDict[[tile[0], tile[1]]] = true;
    }
    
    let loaded = Object.keys(loadedTiles);
    for (let i = 0; i < loaded.length; ++i) {
        if (tilesDict.hasOwnProperty(loaded[i])) continue;
        let tile = loaded[i].split(",");
        unloadTile(parseInt(tile[0]), parseInt(tile[1]));
    }
    
    for (let i = 0; i < tiles.length; ++i) {
        let tile = tiles[i]
        loadTile(tile[0], tile[1], 13);
    }
    
    selectedObj = null;
}


rwySel.addEventListener("change", (e) => {
    curRwy = rwySel.options[rwySel.selectedIndex].value;
    loadProc();
});

transSel.addEventListener("change", (e) => {
    curTrans = transSel.options[transSel.selectedIndex].value;
    loadProc();
});

function registerProcClickListener(node, proc) {
    node.addEventListener("click", () => initProc(proc));
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

let popupArea = $("popup-cover");
let popupLicense = $("license-popup");
let popupInvalid = $("invalid-airport-popup");
let popupInvalidText = $("invalid-airport-popup-text");

function hidePopups() {
    popupArea.classList.add("hidden");
    popupLicense.classList.add("hidden");
    popupInvalid.classList.add("hidden");
}

async function submit_icao(val) {
    
    val = val.trim().toUpperCase();
    let res = await fetch("../airport/" + val);
    if (res.status == 404) {
        let text;
        if (!val) {
            text = "Please enter an airport.";
        } else {
            text = "Airport \"" + val + "\" not found.";
        }
        popupInvalidText.textContent = text;
        popupArea.classList.remove("hidden");
        popupLicense.classList.add("hidden");
        popupInvalid.classList.remove("hidden");
        submitLock = false;
        return;
    }
    curAirport = val;
    let data = await res.json();
    populateAirportData(data);
    submitLock = false;
}

$("close-invalid-button").addEventListener("click", () => {
    hidePopups();
})

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

var jobs = {}
var jobArea = $("job-area")
function addJobStatus(id, status) {
    jobArea.classList.remove("hidden");
    let node = jobTemplate.cloneNode(true);
    jobs[id] = node;
    populateChild(node, "job-status", status);
    jobArea.appendChild(node);
}

function updateJobStatus(id, status) {
    let node = jobs[id];
    jobs[id] = node;
    populateChild(node, "job-status", status);
}

function removeJobStatus(id) {
    let node = jobs[id];
    jobArea.removeChild(node);
    delete jobs[id];
    if (Object.keys(jobs).length == 0) {
        jobArea.classList.add("hidden");
    }
}

var loadingTiles = {};
var loadedTiles = {};

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function ensure_url(url, jobId) {
    while (true) {
        let res = await fetch(url);
        if (res.status == 202) {
            updateJobStatus(jobId, await res.text());
            await sleep(200);
        } else {
            updateJobStatus(jobId, "Loading prepared file from server...");
            let obj = URL.createObjectURL(await res.blob());
            removeJobStatus(jobId)
            return obj;
        }
    }
}

function unloadTile(lat, lon) {
    if (loadingTiles[[lat, lon]]) return;
    
    let obj = loadedTiles[[lat, lon]];
    scene.remove(obj);
    delete loadedTiles[[lat, lon]];
}

async function loadTile(lat, lon, zl) {
    if (loadingTiles[[lat, lon]] || loadedTiles[[lat, lon]]) return
    
    loadingTiles[[lat, lon]] = 1
    
    // ensure the things that need loading
    // photo URL
    let photo = `../photo/${lat}/${lon}/${zl}.jpg`;
    let terr = `../terrain/${lat}/${lon}.obj`;
    
    let jobPhoto = `${lat},${lon}_photo`;
    let jobTerr = `${lat},${lon}_terr`;
    
    addJobStatus(jobPhoto, `Preparing to create images for tile ${lat}, ${lon}...`)
    addJobStatus(jobTerr, `Preparing to create terrain for tile ${lat}, ${lon}...`)

    let a = ensure_url(photo, jobPhoto);
    let b = ensure_url(terr, jobTerr);

    let [photoBlob, terrBlob] = await Promise.all([a, b]);
    
    let jobLoad = `${lat},${lon}_load`;
    addJobStatus(jobLoad, `Loading tile ${lat}, ${lon}...`)

    let mtl = new MTLLoader();
    mtl.load(
        'terrain.mtl',
        function (materials) {
            materials.preload();
            const loader = new OBJLoader();
            loader.setMaterials(materials);
            loader.load(
                terrBlob,
                function (object) {
                    var texture = new THREE.TextureLoader().load(photoBlob);

                    object.traverse(function (child) {
                        if (child instanceof THREE.Mesh) {
                            child.material.map = texture;
                        }
                    });
                    scene.add(object);
                    delete loadingTiles[[lat, lon]];
                    loadedTiles[[lat, lon]] = object;
                    removeJobStatus(jobLoad);
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
    // go_to_pos(lat, lon, 1000)
}


do_debug();
