const { app } = window.comfyAPI.app;

app.registerExtension({
    name: "IFMSDownload",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeType.comfyClass === "IF_MSDownload") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                onNodeCreated?.apply(this, arguments);

                this.element.classList.add('IF-MSDownload-node');

                // Progress bar
                this.addWidget("progressbar", "Progress", "progress", 0, 1);
                this.progressBarWidget = this.widgets[this.widgets.length - 1];

                // Input titles
                this.inputs?.forEach(input => {
                    const widget = this.widgets.find(w => w.name === input.name);
                    if (widget && widget.element && widget.element.parentNode) {
                        const title = document.createElement("div");
                        title.className = "IF-input-title";
                        title.textContent = this.getInputTitle(input.name);
                        widget.element.parentNode.insertBefore(title, widget.element);
                    }
                });
            };

            nodeType.prototype.getInputTitle = function(inputName) {
                const titles = {
                    model_id: "Model ID",
                    file_paths: "File Paths",
                    folder_path: "Download Folder",
                    exclude_files: "Exclude Files",
                    provided_token: "ModelScope Token",
                    mode: "Download Mode"
                };
                return titles[inputName] || inputName;
            };

            // Handle progress updates from backend
            nodeType.prototype.onExecuted = function(message) {
                if (message.progress !== undefined && this.progressBarWidget) {
                    this.progressBarWidget.value = message.progress.value;
                    this.progressBarWidget.max = message.progress.max;
                    if (message.progress.text) {
                        this.progressBarWidget.innerText = message.progress.text;
                    }
                    this.setDirtyCanvas(true, false);
                }
            };
        }
    }
});


