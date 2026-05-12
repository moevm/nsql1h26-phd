class Utils {
    static showMessage(message, type = 'info', duration = 3000) {
        const existingMessages = document.querySelectorAll('.message-toast');
        existingMessages.forEach(msg => msg.remove());

        const messageDiv = document.createElement('div');
        messageDiv.className = `message-toast message-${type}`;
        messageDiv.textContent = message;

        const colors = {
            error: '#ef4444',
            info: '#3b82f6',
            success: '#10b981',
            warning: '#f59e0b'
        };

        Object.assign(messageDiv.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '500',
            zIndex: '1000',
            maxWidth: '300px',
            wordWrap: 'break-word',
            backgroundColor: colors[type] || colors.info,
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            transform: 'translateX(0)',
            transition: 'transform 0.3s ease',
            cursor: 'pointer'
        });

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.style.transform = 'translateX(0)';
        }, 10);

        setTimeout(() => {
            messageDiv.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.parentNode.removeChild(messageDiv);
                }
            }, 300);
        }, duration);

        messageDiv.addEventListener('click', () => {
            messageDiv.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.parentNode.removeChild(messageDiv);
                }
            }, 300);
        });
    }

    static showErrorMessage(message, duration = 3000) {
        this.showMessage(message, 'error', duration);
    }

    static showInfoMessage(message, duration = 3000) {
        this.showMessage(message, 'info', duration);
    }

    static formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

window.Utils = Utils;
