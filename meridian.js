import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function path_stem(path) {
    let last_sep = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
    if (last_sep < 0) return ["", path];
    return [path.slice(0, last_sep + 1), path.slice(last_sep + 1)];
}

async function scanDirectory(node, path) {
    if (!path || path.trim() === "") {
        node._meridian_status = null;
        node.setDirtyCanvas(true, true);
        return;
    }
    try {
        const resp = await fetch(api.apiURL("/meridian/scandir?" + new URLSearchParams({ path })));
        const data = await resp.json();
        if (data.error) {
            node._meridian_scan = { error: data.error };
        } else {
            const batchWidget = node.widgets?.find(w => w.name === "batch_size");
            const overlapWidget = node.widgets?.find(w => w.name === "overlap_frames");
            const batchSize = batchWidget?.value || 30;
            const overlap = overlapWidget?.value || 4;
            const stride = Math.max(1, batchSize - overlap);
            const totalBatches = Math.ceil(data.frame_count / stride);
            node._meridian_scan = { frame_count: data.frame_count, total_batches: totalBatches };
        }
    } catch(e) {
        node._meridian_scan = { error: "Could not reach server" };
    }
    node._meridian_status = null;
    node.setDirtyCanvas(true, true);
}

function addPathCompletion(widget, node) {
    const originalMouse = widget.mouse;
    widget.mouse = function(event, pos, n) {
        if (event.type === "pointerdown" && event.button === 0) {
            showPathDialog.call(this, event, n);
            return true;
        }
        return originalMouse?.apply(this, arguments);
    };

    // Scan when value changes
    const originalCallback = widget.callback;
    widget.callback = function(value) {
        scanDirectory(node, value);
        return originalCallback?.apply(this, arguments);
    };
}

function showPathDialog(event, node) {
    if (this.prompt) return;
    this.prompt = true;

    const pathWidget = this;
    const dialog = document.createElement("div");
    dialog.className = "litegraph litesearchbox graphdialog rounded";
    dialog.innerHTML = '<span class="name">Directory</span><input autofocus="" type="text" class="value"><button class="rounded">OK</button><div class="helper"></div>';
    dialog.close = () => { dialog.remove(); pathWidget.prompt = false; };
    document.body.appendChild(dialog);

    const input = dialog.querySelector(".value");
    const optionsEl = dialog.querySelector(".helper");
    const button = dialog.querySelector("button");
    input.value = pathWidget.value || "";

    let timeout = null;
    let last_path = null;
    let options = [];

    async function updateOptions() {
        timeout = null;
        const [path, remainder] = path_stem(input.value);
        if (last_path !== path) {
            try {
                const resp = await fetch(api.apiURL("/meridian/getpath?" + new URLSearchParams({ path })));
                options = await resp.json();
            } catch(e) {
                options = [];
            }
            last_path = path;
        }
        optionsEl.innerHTML = "";
        for (const option of options) {
            if (!option.startsWith(remainder)) continue;
            const el = document.createElement("div");
            el.innerText = option;
            el.className = "litegraph lite-search-item" + (option.endsWith("/") ? " is-dir" : "");
            el.addEventListener("click", () => {
                if (option.endsWith("/")) {
                    input.value = last_path + option;
                    if (timeout) clearTimeout(timeout);
                    timeout = setTimeout(updateOptions, 10);
                } else {
                    pathWidget.value = last_path + option;
                    if (pathWidget.callback) pathWidget.callback(pathWidget.value);
                    dialog.close();
                }
            });
            optionsEl.appendChild(el);
        }
    }

    input.addEventListener("keydown", (e) => {
        if (e.keyCode === 27) {
            dialog.close();
        } else if (e.keyCode === 13) {
            pathWidget.value = input.value;
            if (pathWidget.callback) pathWidget.callback(pathWidget.value);
            dialog.close();
        } else if (e.keyCode === 9) {
            if (optionsEl.firstChild) {
                input.value = last_path + optionsEl.firstChild.innerText;
            }
            e.preventDefault();
            e.stopPropagation();
        } else {
            if (timeout) clearTimeout(timeout);
            timeout = setTimeout(updateOptions, 10);
            return;
        }
        e.preventDefault();
        e.stopPropagation();
    });

    button.addEventListener("click", () => {
        pathWidget.value = input.value;
        if (pathWidget.callback) pathWidget.callback(pathWidget.value);
        node.graph.setDirtyCanvas(true);
        dialog.close();
    });

    const rect = app.canvas.canvas.getBoundingClientRect();
    dialog.style.left = (event.clientX - rect.left - 20) + "px";
    dialog.style.top = (event.clientY - rect.top - 20) + "px";

    setTimeout(async () => {
        input.focus();
        await updateOptions();
    }, 10);
}

app.registerExtension({
    name: "meridian.temporalbatchloader",

    async setup() {
        api.addEventListener("meridian.status", (event) => {
            const { node_id, status, frame_start, frame_end, current_batch, total_batches } = event.detail;
            const node = app.graph.getNodeById(parseInt(node_id));
            if (!node) return;
            node._meridian_status = { status, frame_start, frame_end, current_batch, total_batches };
            node._meridian_scan = null;
            node.setDirtyCanvas(true, true);
        });
    },

    async nodeCreated(node) {
        if (node.comfyClass !== "TemporalBatchLoader") return;

        const dirWidget = node.widgets?.find(w => w.name === "directory");
        if (dirWidget) {
            addPathCompletion(dirWidget, node);
            // Scan on load if directory already set
            if (dirWidget.value) {
                setTimeout(() => scanDirectory(node, dirWidget.value), 500);
            }
        }

        // Re-scan when batch_size or overlap_frames change
        const batchWidget = node.widgets?.find(w => w.name === "batch_size");
        const overlapWidget = node.widgets?.find(w => w.name === "overlap_frames");
        const rescan = () => {
            const dir = node.widgets?.find(w => w.name === "directory")?.value;
            if (dir) scanDirectory(node, dir);
        };
        if (batchWidget) { const orig = batchWidget.callback; batchWidget.callback = function(v) { rescan(); return orig?.apply(this, arguments); }; }
        if (overlapWidget) { const orig = overlapWidget.callback; overlapWidget.callback = function(v) { rescan(); return orig?.apply(this, arguments); }; }

        node.onDrawForeground = function(ctx) {
            const x = 10;
            const y = this.size[1] - 30;

            ctx.save();
            ctx.font = "bold 12px monospace";
            ctx.textAlign = "left";

            if (this._meridian_status) {
                const { status, frame_start, frame_end, current_batch, total_batches } = this._meridian_status;
                if (status === "Complete") {
                    ctx.fillStyle = "#00ff99";
                    ctx.fillText(`✅ Complete  ${total_batches}/${total_batches} batches`, x, y);
                } else if (status === "Running") {
                    ctx.fillStyle = "#ffffff";
                    ctx.fillText(`Frames: ${frame_start} → ${frame_end}   Batch: ${current_batch}/${total_batches}`, x, y);
                } else {
                    ctx.fillStyle = "#ff9900";
                    ctx.fillText(`⚠️ ${status}`, x, y);
                }
            } else if (this._meridian_scan) {
                if (this._meridian_scan.error) {
                    ctx.fillStyle = "#ff9900";
                    ctx.fillText(`⚠️ ${this._meridian_scan.error}`, x, y);
                } else {
                    const { frame_count, total_batches } = this._meridian_scan;
                    ctx.fillStyle = "#aaaaaa";
                    ctx.fillText(`📁 ${frame_count} frames  —  ${total_batches} batches`, x, y);
                }
            }

            ctx.restore();
        };
    },
});
