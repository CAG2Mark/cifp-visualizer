function $(val) {
    return document.getElementById(val);
}

let sidArea = $("sidebar-sid-area");
let starArea = $("sidebar-star-area");
let appchArea = $("sidebar-approach-area");

let sidBtn = $("proc-sid");
let starBtn = $("proc-star");
let appchBtn = $("proc-approach");

sidBtn.addEventListener("change", () => {
    sidArea.classList.remove("hidden");
    starArea.classList.add("hidden");
    appchArea.classList.add("hidden");
})

starBtn.addEventListener("change", () => {
    sidArea.classList.add("hidden");
    starArea.classList.remove("hidden");
    appchArea.classList.add("hidden");
})

appchBtn.addEventListener("change", () => {
    sidArea.classList.add("hidden");
    starArea.classList.add("hidden");
    appchArea.classList.remove("hidden");
})
