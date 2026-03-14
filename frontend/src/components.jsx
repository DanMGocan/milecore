import { createPortal } from 'react-dom';

export function Modal({ open, onClose, title, children }) {
    if (!open) return null;
    return createPortal(
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
            <div className="modal">
                <button className="modal-close" onClick={onClose}>&times;</button>
                <h3>{title}</h3>
                {children}
            </div>
        </div>,
        document.body
    );
}
