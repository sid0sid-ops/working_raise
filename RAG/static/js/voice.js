/** Voice & Audio Interaction Module */
import { ToastSystem } from './toast.js';

export const VoiceModule = {
    speechRate: 1.0,
    recognition: null,
    isListening: false,

    setRate(rate) {
        this.speechRate = parseFloat(rate) || 1.0;
    },

    speakAnswer(msgId) {
        const body = document.getElementById(`answerBody_${msgId}`);
        if (!body) return;

        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            ToastSystem.show("Read aloud stopped");
            return;
        }

        const cleanText = body.innerText.replace(/\[\d+\]/g, "");
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = this.speechRate;
        window.speechSynthesis.speak(utterance);
        ToastSystem.show("Reading aloud...");
    },

    toggleInput() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            ToastSystem.show("Speech recognition not supported in this browser.");
            return;
        }

        if (this.isListening && this.recognition) {
            this.recognition.stop();
            this.isListening = false;
            ToastSystem.show("Microphone off");
            return;
        }

        this.recognition = new SpeechRec();
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        this.recognition.lang = "en-US";

        this.recognition.onstart = () => {
            this.isListening = true;
            ToastSystem.show("Listening... Speak your research question");
            const btn = document.getElementById("voiceInputBtn");
            if (btn) btn.style.color = "#f87171";
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            const input = document.getElementById("queryInput");
            if (input) {
                input.value = transcript;
                input.dispatchEvent(new Event("input"));
            }
        };

        this.recognition.onend = () => {
            this.isListening = false;
            const btn = document.getElementById("voiceInputBtn");
            if (btn) btn.style.color = "";
        };

        this.recognition.start();
    }
};
