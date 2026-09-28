document.addEventListener("DOMContentLoaded", () => {
    /* =========================================================
       SUMMARIX AI - WORKSPACE JAVASCRIPT
       ========================================================= */

    let selectedFile = null;
    let selectedTool = "summary";
    let chatHistory = [];
    let chatSending = false;
    let editingMessageIndex = null;

    /* =========================================================
       ELEMENT REFERENCES
       ========================================================= */

    const fileInput = document.getElementById("fileInput");
    const browseBtn = document.getElementById("browseBtn");
    const dropZone = document.getElementById("dropZone");

    const uploadForm = document.getElementById("uploadForm");
    const uploadBtn = document.getElementById("uploadBtn");
    const uploadStatus = document.getElementById("uploadStatus");

    const selectedFileBox = document.getElementById("selectedFile");

    const documentSection = document.getElementById("documentSection");
    const documentName = document.getElementById("documentName");
    const documentLength = document.getElementById("documentLength");

    const clearBtn = document.getElementById("clearBtn");
    const processBtn = document.getElementById("processBtn");

    const customQuery = document.getElementById("customQuery");

    const resultSection = document.getElementById("resultSection");
    const result = document.getElementById("result");
    const copyBtn = document.getElementById("copyBtn");

    const chatMessages = document.getElementById("chatMessages");
    const chatInput = document.getElementById("chatInput");
    const chatSend = document.getElementById("chatSend");
    const chatRemaining = document.getElementById("chatRemaining");

    /* =========================================================
       INITIALIZATION
       ========================================================= */

    initialize();

    function initialize() {
        setupFileUpload();
        setupUploadForm();
        setupToolButtons();
        setupProcessButton();
        setupClearButton();
        setupCopyButton();
        setupChat();

        loadDocumentInfo();
        loadChatStatus();

        console.log("SUMMARIX AI Workspace initialized.");
    }

    /* =========================================================
       FILE UPLOAD
       ========================================================= */

    function setupFileUpload() {

        if (browseBtn && fileInput) {
            browseBtn.addEventListener("click", () => {
                fileInput.click();
            });
        }

        if (fileInput) {
            fileInput.addEventListener("change", (event) => {
                const files = event.target.files;

                if (files && files.length > 0) {
                    handleFileSelection(files[0]);
                }
            });
        }

        if (dropZone) {

            dropZone.addEventListener("dragover", (event) => {
                event.preventDefault();
                dropZone.classList.add("drag-over");
            });

            dropZone.addEventListener("dragleave", () => {
                dropZone.classList.remove("drag-over");
            });

            dropZone.addEventListener("drop", (event) => {

                event.preventDefault();
                dropZone.classList.remove("drag-over");

                const files = event.dataTransfer.files;

                if (files && files.length > 0) {
                    handleFileSelection(files[0]);
                }
            });
        }
    }
function handleFileSelection(file) {

    if (!file) {
        return;
    }

    const extension = file.name
        .split(".")
        .pop()
        .toLowerCase();

    if (extension !== "pdf" && extension !== "docx") {

        showUploadStatus(
            "Only PDF and DOCX files are supported.",
            "error"
        );

        return;
    }

    const maxSize = 20 * 1024 * 1024;

    if (file.size > maxSize) {

        showUploadStatus(
            "File is too large. Maximum size is 20 MB.",
            "error"
        );

        return;
    }

    selectedFile = file;

    /* Show selected document name immediately */
    if (documentName) {
        documentName.textContent = file.name;
        documentName.style.display = "block";
    }

    /* Show file card if available */
    if (selectedFileBox) {
        displaySelectedFile(file);
    }

    hideUploadStatus();
}

    /* =========================================================
       DISPLAY SELECTED FILE
       ========================================================= */

    function displaySelectedFile(file) {

        if (!selectedFileBox) {
            return;
        }

        const sizeMB = (
            file.size / (1024 * 1024)
        ).toFixed(2);

        selectedFileBox.style.display = "flex";

        selectedFileBox.innerHTML = `
            <div class="selected-file-icon">
                📄
            </div>

            <div class="selected-file-details">
                <strong>${escapeHtml(file.name)}</strong>
                <small>${sizeMB} MB</small>
            </div>

            <button
                type="button"
                class="remove-file-btn"
                id="removeFileBtn"
                aria-label="Remove selected file"
            >
                ✕
            </button>
        `;

        const removeButton =
            document.getElementById("removeFileBtn");

        if (removeButton) {
            removeButton.addEventListener(
                "click",
                removeSelectedFile
            );
        }
    }

    /* =========================================================
       REMOVE SELECTED FILE
       ========================================================= */

    function removeSelectedFile() {

        selectedFile = null;

        if (fileInput) {
            fileInput.value = "";
        }

        if (selectedFileBox) {
            selectedFileBox.innerHTML = "";
            selectedFileBox.style.display = "none";
        }

        hideUploadStatus();
    }

    /* =========================================================
       UPLOAD FORM
       ========================================================= */

    function setupUploadForm() {

        if (!uploadForm) {
            return;
        }

        uploadForm.addEventListener("submit", async (event) => {

            event.preventDefault();

            await uploadDocument();
        });
    }

    /* =========================================================
       UPLOAD DOCUMENT
       ========================================================= */

    async function uploadDocument() {

        if (!selectedFile) {

            showUploadStatus(
                "Please select a PDF or DOCX file first.",
                "error"
            );

            return;
        }

        setUploadLoading(true);
        hideUploadStatus();

        const formData = new FormData();

        formData.append("file", selectedFile);

        try {

            const response = await fetch(
                "/upload-document",
                {
                    method: "POST",
                    body: formData
                }
            );

            let data;

            try {
                data = await response.json();
            } catch {
                data = {};
            }

            if (response.ok && data.success) {

                showUploadStatus(
                    data.message ||
                    "Document uploaded successfully.",
                    "success"
                );

                updateDocumentInfo(
                    data.filename,
                    data.text_length
                );

                if (documentSection) {
                    documentSection.style.display = "block";
                }

                if (resultSection) {
                    resultSection.style.display = "none";
                }

                setTimeout(() => {

                    if (documentSection) {

                        documentSection.scrollIntoView({
                            behavior: "smooth",
                            block: "start"
                        });
                    }

                }, 250);

            } else {

                showUploadStatus(
                    data.error || "Upload failed.",
                    "error"
                );
            }

        } catch (error) {

            console.error("Upload error:", error);

            showUploadStatus(
                "Could not connect to the server.",
                "error"
            );

        } finally {

            setUploadLoading(false);
        }
    }

    /* =========================================================
       UPLOAD BUTTON STATE
       ========================================================= */

    function setUploadLoading(loading) {

        if (!uploadBtn) {
            return;
        }

        uploadBtn.disabled = loading;

        uploadBtn.textContent = loading
            ? "Uploading..."
            : "Upload Document";
    }

    /* =========================================================
       UPLOAD STATUS
       ========================================================= */

    function showUploadStatus(message, type) {

        if (!uploadStatus) {
            return;
        }

        uploadStatus.textContent = message;

        uploadStatus.className =
            "status-message " + type;

        uploadStatus.style.display = "block";
    }

    function hideUploadStatus() {

        if (!uploadStatus) {
            return;
        }

        uploadStatus.textContent = "";
        uploadStatus.style.display = "none";
    }

    /* =========================================================
       DOCUMENT INFORMATION
       ========================================================= */

    function updateDocumentInfo(filename, textLength) {

        if (documentName) {

            documentName.textContent =
                filename || "Document";
        }

        if (documentLength) {

            const length = Number(textLength || 0);

            documentLength.textContent =
                "Text length: " +
                length.toLocaleString() +
                " characters";
        }
    }

    /* =========================================================
       LOAD CURRENT DOCUMENT
       ========================================================= */

    async function loadDocumentInfo() {

        try {

            const response = await fetch(
                "/document-info",
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            if (!response.ok) {
                return;
            }

            const data = await response.json();

            if (data.success && data.filename) {

                updateDocumentInfo(
                    data.filename,
                    data.text_length
                );

                if (documentSection) {
                    documentSection.style.display = "block";
                }
            }

        } catch (error) {

            console.error(
                "Document info error:",
                error
            );
        }
    }

    /* =========================================================
       TOOL BUTTONS
       ========================================================= */

    function setupToolButtons() {

        const toolButtons =
            document.querySelectorAll(".tool-btn");

        toolButtons.forEach((button) => {

            button.addEventListener("click", () => {

                toolButtons.forEach((btn) => {
                    btn.classList.remove("active");
                });

                button.classList.add("active");

                selectedTool =
                    button.dataset.tool || "summary";

                console.log(
                    "Selected tool:",
                    selectedTool
                );
            });
        });
    }

    /* =========================================================
       PROCESS BUTTON
       ========================================================= */

    function setupProcessButton() {

        if (!processBtn) {
            return;
        }

        processBtn.addEventListener(
            "click",
            processDocument
        );
    }

    /* =========================================================
       PROCESS DOCUMENT
       ========================================================= */

    async function processDocument() {

        if (!selectedTool) {
            selectedTool = "summary";
        }

        if (processBtn) {

            processBtn.disabled = true;

            processBtn.textContent =
                "Processing...";
        }

        if (resultSection) {
            resultSection.style.display = "block";
        }

        if (result) {

            result.innerHTML = `
                <div class="loading-result">
                    <div class="loading-spinner"></div>

                    <p>
                        SUMMARIX AI is processing your document...
                    </p>
                </div>
            `;
        }

        const query =
            customQuery
                ? customQuery.value.trim()
                : "";

        try {

            const response = await fetch(
                "/process",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json"
                    },

                    body: JSON.stringify({
                        tool: selectedTool,
                        custom_query: query
                    })
                }
            );

            let data;

            try {
                data = await response.json();
            } catch {
                data = {};
            }

            if (response.ok && data.success) {

                displayResult(
                    data.result || ""
                );

            } else {

                displayResult(
                    data.error ||
                    "Unable to process the document."
                );
            }

        } catch (error) {

            console.error(
                "Processing error:",
                error
            );

            displayResult(
                "Could not connect to the AI service."
            );

        } finally {

            if (processBtn) {

                processBtn.disabled = false;

                processBtn.textContent =
                    "Process Document";
            }
        }
    }

    /* =========================================================
       DISPLAY RESULT
       ========================================================= */

    function displayResult(text) {

        if (!result) {
            return;
        }

        result.innerHTML =
            formatAIText(text || "");

        if (resultSection) {

            resultSection.style.display =
                "block";

            setTimeout(() => {

                resultSection.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

            }, 100);
        }
    }

    /* =========================================================
       COPY MAIN RESULT
       ========================================================= */

    function setupCopyButton() {

        if (!copyBtn) {
            return;
        }

        copyBtn.addEventListener(
            "click",
            async () => {

                const text =
                    result
                        ? result.innerText.trim()
                        : "";

                if (!text) {
                    return;
                }

                const originalText =
                    copyBtn.textContent;

                try {

                    await copyText(text);

                    copyBtn.textContent =
                        "✓ Copied";

                    copyBtn.classList.add(
                        "copied"
                    );

                    setTimeout(() => {

                        copyBtn.textContent =
                            originalText;

                        copyBtn.classList.remove(
                            "copied"
                        );

                    }, 1500);

                } catch (error) {

                    console.error(
                        "Copy error:",
                        error
                    );
                }
            }
        );
    }

    /* =========================================================
       CLEAR DOCUMENT
       ========================================================= */

    function setupClearButton() {

        if (!clearBtn) {
            return;
        }

        clearBtn.addEventListener(
            "click",
            clearDocument
        );
    }

    async function clearDocument() {

        if (clearBtn) {
            clearBtn.disabled = true;
        }

        try {

            const response = await fetch(
                "/clear-document",
                {
                    method: "POST",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            let data;

            try {
                data = await response.json();
            } catch {
                data = {};
            }

            if (response.ok && data.success) {

                selectedFile = null;

                if (fileInput) {
                    fileInput.value = "";
                }

                if (selectedFileBox) {

                    selectedFileBox.innerHTML = "";

                    selectedFileBox.style.display =
                        "none";
                }

                if (documentSection) {
                    documentSection.style.display =
                        "none";
                }

                if (resultSection) {
                    resultSection.style.display =
                        "none";
                }

                if (result) {
                    result.innerHTML = "";
                }

                if (customQuery) {
                    customQuery.value = "";
                }

                chatHistory = [];

                editingMessageIndex = null;

                renderChatHistory();

                showUploadStatus(
                    "Document cleared successfully.",
                    "success"
                );

            } else {

                showUploadStatus(
                    data.error ||
                    "Unable to clear the document.",
                    "error"
                );
            }

        } catch (error) {

            console.error(
                "Clear document error:",
                error
            );

            showUploadStatus(
                "Could not connect to the server.",
                "error"
            );

        } finally {

            if (clearBtn) {
                clearBtn.disabled = false;
            }
        }
    }

    /* =========================================================
       CHAT SETUP
       ========================================================= */

    function setupChat() {

        const chatForm =
            document.getElementById("chatForm");

        if (chatForm) {

            chatForm.addEventListener(
                "submit",
                (event) => {

                    event.preventDefault();

                    sendMessage();
                }
            );
        }

        if (chatSend) {

            chatSend.addEventListener(
                "click",
                sendMessage
            );
        }

        if (chatInput) {

            chatInput.addEventListener(
                "keydown",
                (event) => {

                    if (
                        event.key === "Escape" &&
                        editingMessageIndex !== null
                    ) {

                        event.preventDefault();

                        cancelEditing();

                        return;
                    }

                    if (
                        event.key === "Enter" &&
                        !event.shiftKey
                    ) {

                        event.preventDefault();

                        sendMessage();
                    }
                }
            );
        }

        renderChatHistory();
    }

    /* =========================================================
       CHAT HISTORY
       ========================================================= */

    function renderChatHistory() {

        if (!chatMessages) {
            return;
        }

        chatMessages.innerHTML = "";

        if (
            !chatHistory ||
            chatHistory.length === 0
        ) {

            addMessage(
                "assistant",
                "Hello! Upload a document and ask me questions about its content.",
                null
            );

            return;
        }

        chatHistory.forEach(
            (message, index) => {

                addMessage(
                    message.role,
                    message.content,
                    index
                );
            }
        );

        chatMessages.scrollTop =
            chatMessages.scrollHeight;
    }

    /* =========================================================
       ADD CHAT MESSAGE
       ========================================================= */

    function addMessage(
        role,
        content,
        historyIndex
    ) {

        if (!chatMessages) {
            return;
        }

        const wrapper =
            document.createElement("div");

        wrapper.className =
            "chat-message " +
            (
                role === "user"
                    ? "user-message"
                    : "assistant-message"
            );

        if (
            historyIndex !== null &&
            historyIndex !== undefined
        ) {
            wrapper.dataset.index =
                historyIndex;
        }

        const bubble =
            document.createElement("div");

        bubble.className =
            "message-bubble";

        const text =
            document.createElement("div");

        text.className =
            "message-text";

        text.innerHTML =
            formatAIText(content);

        bubble.appendChild(text);

        /* =====================================================
           USER MESSAGE - EDIT
           ===================================================== */

        if (role === "user") {

            const actions =
                document.createElement("div");

            actions.className =
                "message-actions";

            const editButton =
                document.createElement("button");

            editButton.type = "button";

            editButton.className =
                "message-action edit-message";

            editButton.textContent =
                "✏️ Edit";

            editButton.title =
                "Edit message";

            editButton.addEventListener(
                "click",
                () => {

                    startEditingMessage(
                        historyIndex
                    );
                }
            );

            actions.appendChild(
                editButton
            );

            bubble.appendChild(
                actions
            );
        }

        /* =====================================================
           ASSISTANT MESSAGE - COPY
           ===================================================== */

        if (role === "assistant") {

            const actions =
                document.createElement("div");

            actions.className =
                "message-actions";

            const copyButton =
                document.createElement("button");

            copyButton.type = "button";

            copyButton.className =
                "message-action copy-message";

            copyButton.textContent =
                "📋 Copy";

            copyButton.title =
                "Copy response";

            copyButton.addEventListener(
                "click",
                () => {

                    copyMessage(
                        content,
                        copyButton
                    );
                }
            );

            actions.appendChild(
                copyButton
            );

            bubble.appendChild(
                actions
            );
        }

        wrapper.appendChild(
            bubble
        );

        chatMessages.appendChild(
            wrapper
        );
    }

    /* =========================================================
       START EDITING MESSAGE
       ========================================================= */

    function startEditingMessage(index) {

        if (
            index === null ||
            index === undefined
        ) {
            return;
        }

        if (
            !chatHistory[index] ||
            chatHistory[index].role !== "user"
        ) {
            return;
        }

        if (!chatInput) {
            return;
        }

        editingMessageIndex = index;

        chatInput.value =
            chatHistory[index].content;

        chatInput.classList.add(
            "editing-input"
        );

        if (chatSend) {

            chatSend.textContent =
                "Update";

            chatSend.classList.add(
                "editing"
            );
        }

        chatInput.focus();

        chatInput.setSelectionRange(
            chatInput.value.length,
            chatInput.value.length
        );
    }

    /* =========================================================
       CANCEL EDITING
       ========================================================= */

    function cancelEditing() {

        editingMessageIndex = null;

        if (chatInput) {

            chatInput.value = "";

            chatInput.classList.remove(
                "editing-input"
            );
        }

        if (chatSend) {

            chatSend.textContent =
                "Send";

            chatSend.classList.remove(
                "editing"
            );
        }
    }

    /* =========================================================
       COPY CHAT MESSAGE
       ========================================================= */

    async function copyMessage(
        content,
        button
    ) {

        if (!button) {
            return;
        }

        const originalText =
            button.textContent;

        try {

            await copyText(content);

            button.textContent =
                "✓ Copied";

            button.classList.add(
                "copied"
            );

            setTimeout(() => {

                button.textContent =
                    originalText;

                button.classList.remove(
                    "copied"
                );

            }, 1500);

        } catch (error) {

            console.error(
                "Copy failed:",
                error
            );

            button.textContent =
                "Copy failed";

            setTimeout(() => {

                button.textContent =
                    originalText;

            }, 1500);
        }
    }

    /* =========================================================
       SEND CHAT MESSAGE
       ========================================================= */

    async function sendMessage() {

        if (
            !chatInput ||
            chatSending
        ) {
            return;
        }

        const message =
            chatInput.value.trim();

        if (!message) {
            return;
        }

        /* -----------------------------------------------------
           EDIT MODE
           ----------------------------------------------------- */

        if (
            editingMessageIndex !== null
        ) {

            await updateEditedMessage(
                message
            );

            return;
        }

        chatSending = true;

        setChatLoading(true);

        chatHistory.push({
            role: "user",
            content: message
        });

        chatInput.value = "";

        renderChatHistory();

        showTyping();

        try {

            const response =
                await fetch(
                    "/api/chat",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json"
                        },

                        body: JSON.stringify({
                            messages:
                                chatHistory
                        })
                    }
                );

            let data;

            try {
                data = await response.json();
            } catch {
                data = {};
            }

            removeTyping();

            /* -------------------------------------------------
               SUCCESS
               ------------------------------------------------- */

            if (
                response.ok &&
                data.success
            ) {

                const answer =
                    data.response || "";

                chatHistory.push({
                    role: "assistant",
                    content: answer
                });

                renderChatHistory();

                if (
                    typeof data.remaining_messages !==
                    "undefined"
                ) {

                    updateRemaining(
                        data.remaining_messages
                    );
                }

                return;
            }

            /* -------------------------------------------------
               CHAT LIMIT
               ------------------------------------------------- */

            if (data.limit_reached) {

                chatHistory.push({
                    role: "assistant",

                    content:
                        data.error ||
                        "Your chatbot message limit has been reached."
                });

                renderChatHistory();

                updateRemaining(0);

                return;
            }

            /* -------------------------------------------------
               GEMINI QUOTA
               ------------------------------------------------- */

            if (data.quota_exceeded) {

                chatHistory.push({
                    role: "assistant",

                    content:
                        data.error ||
                        "Gemini API usage limit has been reached."
                });

                renderChatHistory();

                return;
            }

            /* -------------------------------------------------
               GENERAL ERROR
               ------------------------------------------------- */

            chatHistory.push({
                role: "assistant",

                content:
                    data.error ||
                    "Sorry, something went wrong."
            });

            renderChatHistory();

        } catch (error) {

            removeTyping();

            console.error(
                "Chatbot error:",
                error
            );

            chatHistory.push({
                role: "assistant",

                content:
                    "Could not connect to the AI service. Please try again."
            });

            renderChatHistory();

        } finally {

            chatSending = false;

            setChatLoading(false);
        }
    }

    /* =========================================================
       UPDATE EDITED MESSAGE
       ========================================================= */

    async function updateEditedMessage(
        newMessage
    ) {

        if (
            editingMessageIndex === null
        ) {
            return;
        }

        const index =
            editingMessageIndex;

        if (
            !chatHistory[index] ||
            chatHistory[index].role !== "user"
        ) {

            cancelEditing();

            return;
        }

        chatSending = true;

        setChatLoading(true);

        /* -----------------------------------------------------
           Replace edited message
           ----------------------------------------------------- */

        chatHistory[index].content =
            newMessage;

        /* -----------------------------------------------------
           Remove old responses after edited message
           ----------------------------------------------------- */

        chatHistory =
            chatHistory.slice(
                0,
                index + 1
            );

        cancelEditing();

        renderChatHistory();

        showTyping();

        try {

            const response =
                await fetch(
                    "/api/chat",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json"
                        },

                        body: JSON.stringify({
                            messages:
                                chatHistory
                        })
                    }
                );

            let data;

            try {
                data = await response.json();
            } catch {
                data = {};
            }

            removeTyping();

            if (
                response.ok &&
                data.success
            ) {

                const answer =
                    data.response || "";

                chatHistory.push({
                    role: "assistant",
                    content: answer
                });

                renderChatHistory();

                if (
                    typeof data.remaining_messages !==
                    "undefined"
                ) {

                    updateRemaining(
                        data.remaining_messages
                    );
                }

            } else {

                chatHistory.push({
                    role: "assistant",

                    content:
                        data.error ||
                        "Unable to regenerate the response."
                });

                renderChatHistory();
            }

        } catch (error) {

            removeTyping();

            console.error(
                "Edited message error:",
                error
            );

            chatHistory.push({
                role: "assistant",

                content:
                    "Could not connect to the AI service. Please try again."
            });

            renderChatHistory();

        } finally {

            chatSending = false;

            setChatLoading(false);
        }
    }

    /* =========================================================
       CHAT LOADING STATE
       ========================================================= */

    function setChatLoading(loading) {

        if (chatInput) {
            chatInput.disabled = loading;
        }

        if (chatSend) {
            chatSend.disabled = loading;
        }
    }

    /* =========================================================
       TYPING INDICATOR
       ========================================================= */

    function showTyping() {

        if (!chatMessages) {
            return;
        }

        removeTyping();

        const wrapper =
            document.createElement("div");

        wrapper.id =
            "chatTyping";

        wrapper.className =
            "typing-message";

        wrapper.innerHTML = `
            <div class="typing-bubble">

                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>

                <span class="typing-text">
                    SUMMARIX AI is typing...
                </span>

            </div>
        `;

        chatMessages.appendChild(
            wrapper
        );

        chatMessages.scrollTop =
            chatMessages.scrollHeight;
    }

    /* =========================================================
       REMOVE TYPING INDICATOR
       ========================================================= */

    function removeTyping() {

        const typing =
            document.getElementById(
                "chatTyping"
            );

        if (typing) {
            typing.remove();
        }
    }

    /* =========================================================
       LOAD CHAT STATUS
       ========================================================= */

    async function loadChatStatus() {

        try {

            const response =
                await fetch(
                    "/api/chat/status",
                    {
                        method: "GET",

                        headers: {
                            "Accept":
                                "application/json"
                        }
                    }
                );

            if (!response.ok) {
                return;
            }

            const data =
                await response.json();

            if (data.success) {

                updateRemaining(
                    data.remaining_messages
                );
            }

        } catch (error) {

            console.error(
                "Could not load chat status:",
                error
            );
        }
    }

    /* =========================================================
       UPDATE REMAINING CHAT COUNT
       ========================================================= */

    function updateRemaining(
        remaining
    ) {

        if (!chatRemaining) {
            return;
        }

        let count =
            Number(remaining);

        if (
            Number.isNaN(count) ||
            count < 0
        ) {
            count = 0;
        }

        chatRemaining.textContent =
            count +
            (
                count === 1
                    ? " message remaining"
                    : " messages remaining"
            );
    }

    /* =========================================================
       COPY TEXT
       ========================================================= */

    async function copyText(text) {

        if (
            navigator.clipboard &&
            window.isSecureContext
        ) {

            await navigator.clipboard.writeText(
                text
            );

            return;
        }

        const textarea =
            document.createElement(
                "textarea"
            );

        textarea.value = text;

        textarea.style.position =
            "fixed";

        textarea.style.left =
            "-9999px";

        textarea.style.top =
            "0";

        textarea.style.opacity =
            "0";

        document.body.appendChild(
            textarea
        );

        textarea.focus();
        textarea.select();

        const successful =
            document.execCommand(
                "copy"
            );

        textarea.remove();

        if (!successful) {
            throw new Error(
                "Copy command failed."
            );
        }
    }

    /* =========================================================
       FORMAT AI TEXT
       ========================================================= */

    function formatAIText(text) {

        if (
            text === null ||
            text === undefined
        ) {
            return "";
        }

        let formatted =
            escapeHtml(String(text));

        /* -----------------------------------------------------
           Bold
           ----------------------------------------------------- */

        formatted =
            formatted.replace(
                /\*\*(.+?)\*\*/g,
                "<strong>$1</strong>"
            );

        /* -----------------------------------------------------
           Italic
           ----------------------------------------------------- */

        formatted =
            formatted.replace(
                /(^|[^\*])\*([^*\n]+)\*(?!\*)/g,
                "$1<em>$2</em>"
            );

        /* -----------------------------------------------------
           Numbered list
           ----------------------------------------------------- */

        formatted =
            formatted.replace(
                /^(\d+)\.\s+(.+)$/gm,
                '<div class="formatted-number">$1. $2</div>'
            );

        /* -----------------------------------------------------
           Bullet list - •
           ----------------------------------------------------- */

        formatted =
            formatted.replace(
                /^•\s+(.+)$/gm,
                '<div class="formatted-bullet">• $1</div>'
            );

        /* -----------------------------------------------------
           Bullet list - -
           ----------------------------------------------------- */

        formatted =
            formatted.replace(
                /^-\s+(.+)$/gm,
                '<div class="formatted-bullet">• $1</div>'
            );

        /* -----------------------------------------------------
           Bullet list - *
           ----------------------------------------------------- */

        formatted =
            formatted.replace(
                /^\*\s+(.+)$/gm,
                '<div class="formatted-bullet">★ $1</div>'
            );

        /* -----------------------------------------------------
           Line breaks
           ----------------------------------------------------- */

        formatted =
            formatted.replace(
                /\r?\n/g,
                "<br>"
            );

        return formatted;
    }

    /* =========================================================
       ESCAPE HTML
       ========================================================= */

    function escapeHtml(text) {

        const div =
            document.createElement(
                "div"
            );

        div.textContent =
            text === null ||
            text === undefined
                ? ""
                : String(text);

        return div.innerHTML;
    }

    /* =========================================================
       RESULT DETECTION
       ========================================================= */

    const resultBox =
        document.querySelector(
            ".result-box"
        );

    if (
        resultBox &&
        resultBox.textContent.trim()
    ) {

        console.log(
            "SUMMARIX AI result loaded."
        );
    }

    /* =========================================================
       GLOBAL FUNCTIONS
       ========================================================= */

    /*
       These functions are exposed globally so that
       existing buttons in index.html can continue
       calling them directly.
    */

    window.removeSelectedFile =
        removeSelectedFile;

    window.startEditingMessage =
        startEditingMessage;

    window.cancelEditing =
        cancelEditing;

    window.sendMessage =
        sendMessage;

    window.clearDocument =
        clearDocument;

    window.processDocument =
        processDocument;

    /* =========================================================
       READY
       ========================================================= */

    console.log(
        "SUMMARIX AI Workspace ready."
    );
});