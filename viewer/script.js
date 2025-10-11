import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js'
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js'


var controls;
var camera, scene, renderer;
var mesh;

init();
animate();

function init() {

    camera = new THREE.PerspectiveCamera( 70, window.innerWidth / window.innerHeight, 1, 1000 );
    camera.position.z = 5;

    scene = new THREE.Scene();

    let light = new THREE.DirectionalLight(0xffffff);
    light.position.set(100, 200, 400);
    scene.add(light);
    
    const loader = new OBJLoader();
    loader.load(
        'out.obj',
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


    renderer = new THREE.WebGLRenderer();

    // set the background color to gray
    renderer.setClearColor( 0xa0a0a0 );

    renderer.setPixelRatio( window.devicePixelRatio );
    renderer.setSize( window.innerWidth, window.innerHeight );
    document.body.appendChild( renderer.domElement );

    // let's have the mouse affect the view
    controls = new OrbitControls( camera, renderer.domElement );

    //

    window.addEventListener( 'resize', onWindowResize, false );

}

function onWindowResize() {

    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize( window.innerWidth, window.innerHeight );

}

function animate() {

    requestAnimationFrame( animate );

    // auto-rotation at start - turn it off
    //mesh.rotation.x += 0.005;
    //mesh.rotation.y += 0.01;

    renderer.render( scene, camera );
    // have the mouse update the view
    controls.update();

}
