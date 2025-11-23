document.addEventListener('DOMContentLoaded', () => {
    // --- Preloader ---
    const preloader = document.getElementById('preloader');
    if (preloader) {
        window.addEventListener('load', () => {
            setTimeout(() => {
                preloader.classList.add('loaded');
            }, 1800);
        });
    }

    // --- Setup Background Video Rotation ---
    setupBackgroundVideoRotation();

    // --- Active Nav Link ---
    const navLinks = document.querySelectorAll('.navbar .nav-links a');
    const currentPath = window.location.pathname.split("/").pop();
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath || (currentPath === '' && link.getAttribute('href') === 'index.html')) {
            link.classList.add('active');
        }
    });

    // --- Responsive Navigation ---
    const navToggle = document.querySelector('.nav-toggle');
    const navLinksWrapper = document.querySelector('.nav-links-wrapper');
    const allNavLinksInMobileMenu = document.querySelectorAll('.nav-links-wrapper .nav-links a'); 

    if (navToggle && navLinksWrapper) {
        navToggle.addEventListener('click', () => {
            const isNavOpen = document.body.classList.toggle('nav-open');
            navToggle.setAttribute('aria-expanded', isNavOpen);
        });

        allNavLinksInMobileMenu.forEach(link => {
            link.addEventListener('click', () => {
                if (document.body.classList.contains('nav-open')) {
                    document.body.classList.remove('nav-open');
                    navToggle.setAttribute('aria-expanded', 'false');
                }
            });
        });
    }

    // --- CHATBOT FUNCTIONALITY (Updated for Render) ---
    const chatbotIcon = document.getElementById('chatbot-icon');
    const chatbotContainer = document.getElementById('chatbot-container');
    const closeChatbotBtn = document.getElementById('close-chatbot');
    const chatbotMessages = document.getElementById('chatbot-messages');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSendBtn = document.getElementById('chatbot-send-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');

    // 1. CONNECT TO YOUR RENDER BACKEND
    const RENDER_URL = "https://whatsapp-bot-64p9.onrender.com";

    if (chatbotIcon) {
        chatbotIcon.addEventListener('click', () => {
            chatbotContainer.classList.toggle('open');
            if (chatbotContainer.classList.contains('open') && chatbotMessages.children.length === 0) {
                addMessageToChat("Hello! I'm Jace's AI assistant. How can I help you today?", 'bot'); 
            }
        });
    }

    if (closeChatbotBtn) {
        closeChatbotBtn.addEventListener('click', () => {
            chatbotContainer.classList.remove('open');
        });
    }

    if (chatbotSendBtn) {
        chatbotSendBtn.addEventListener('click', sendMessage);
    }

    if (chatbotInput) {
        chatbotInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault(); 
                sendMessage();
            }
        });
    }
    
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', () => {
            chatbotMessages.innerHTML = ''; 
            addMessageToChat("Chat history cleared. How can I assist you now?", 'bot');
        });
    }

    function addMessageToChat(message, sender) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', sender);
        messageElement.textContent = message; 
        chatbotMessages.appendChild(messageElement);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight; 
    }
    
    function addThinkingIndicator() {
        const thinkingElement = document.createElement('div');
        thinkingElement.classList.add('chat-message', 'bot', 'thinking');
        thinkingElement.id = 'thinking-indicator';
        chatbotMessages.appendChild(thinkingElement);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }

    function removeThinkingIndicator() {
        const thinkingElement = document.getElementById('thinking-indicator');
        if (thinkingElement) {
            thinkingElement.remove();
        }
    }

    async function sendMessage() {
        const userMessage = chatbotInput.value.trim();
        if (userMessage === '') return;

        addMessageToChat(userMessage, 'user');
        chatbotInput.value = '';
        addThinkingIndicator();

        try {
            // 2. SEND MESSAGE TO RENDER SERVER
            const response = await fetch(`${RENDER_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage })
            });
            
            removeThinkingIndicator();

            if (!response.ok) {
                throw new Error("Server response not ok");
            }

            const data = await response.json();
            // 3. DISPLAY REPLY
            addMessageToChat(data.reply, 'bot');

        } catch (error) {
            removeThinkingIndicator();
            console.error('Error sending message to Render:', error);
            addMessageToChat('My brain (the server) is currently sleeping or restarting. Please wait 1 minute and try again.', 'bot');
        }
    }

    // --- Smooth Scroll ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const hrefAttribute = this.getAttribute('href');
            if (hrefAttribute && hrefAttribute.length > 1) { 
                try {
                    const targetElement = document.querySelector(hrefAttribute);
                    if (targetElement) {
                        e.preventDefault();
                        targetElement.scrollIntoView({ behavior: 'smooth' });
                    }
                } catch (error) {
                    console.warn(`Smooth scroll failed for
