import type { FC } from "react";
import { useEffect } from "react";

interface ImageModalProps {
  src: string;
  alt: string;
  isOpen: boolean;
  onClose: () => void;
}

const ImageModal: FC<ImageModalProps> = ({ src, alt, isOpen, onClose }) => {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div 
      className="image-modal-overlay"
      onClick={onClose}
    >
      <div 
        className="image-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="image-modal-close"
          onClick={onClose}
          title="关闭 (按 ESC)"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
        <img 
          src={src} 
          alt={alt}
          className="image-modal-image"
        />
        <div className="image-modal-info">
          {alt && <p>{alt}</p>}
        </div>
      </div>
    </div>
  );
};

export default ImageModal;
