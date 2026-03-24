import { app } from "../../scripts/app.js";

app.registerExtension({
	name: "Meridian.Display",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "TemporalBatchLoader") {
			const onNodeCreated = nodeType.prototype.onNodeCreated;
			nodeType.prototype.onNodeCreated = function () {
				const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
				
				// Create the widget and ensure it's visible
				this.displayWidget = this.addWidget("text", "course_status", "WAITING...", () => {}, { serialize: false });
				this.displayWidget.disabled = true;
                this.serialize_widgets = true;
				
				return r;
			};

			const onExecuted = nodeType.prototype.onExecuted;
			nodeType.prototype.onExecuted = function (message) {
				onExecuted?.apply(this, arguments);
				// Check for 'text' in the UI message from Python
				if (message?.text && message.text.length > 0) {
					this.displayWidget.value = message.text[0];
				}
                this.setDirtyCanvas(true);
			};
		}
	},
});
