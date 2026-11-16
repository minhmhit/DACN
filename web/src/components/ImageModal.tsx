import React, { useEffect } from 'react';
import { X, ZoomIn, Download, ExternalLink } from 'lucide-react';

interface ImageModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageSrc: string;
  title: string;
  caption: string;
  analysisText?: string;
}

export const ImageModal: React.FC<ImageModalProps> = ({
  isOpen,
  onClose,
  imageSrc,
  title,
  caption,
  analysisText,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    } else {
      document.body.style.overflow = 'auto';
    }
    return () => {
      document.body.style.overflow = 'auto';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-sm animate-fadeIn">
      <div 
        className="relative flex flex-col max-h-[92vh] max-w-5xl w-full bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-lg bg-blue-100 text-blue-800">
              <ZoomIn className="w-5 h-5" />
            </span>
            <div>
              <h3 className="text-lg font-bold text-slate-900 font-sans">{title}</h3>
              <p className="text-xs text-slate-500">Độ phân giải chuẩn khoa học 300 DPI</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={imageSrc}
              download
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 hover:text-blue-700 transition-colors"
            >
              <Download className="w-4 h-4" />
              Tải ảnh gốc
            </a>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div className="flex justify-center p-2 bg-slate-100 rounded-xl border border-slate-200">
            <img
              src={imageSrc}
              alt={title}
              className="max-h-[60vh] object-contain rounded-lg shadow-sm"
            />
          </div>

          <div className="p-4 bg-blue-50/70 border border-blue-100 rounded-xl">
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-1 flex items-center gap-1.5">
              <ExternalLink className="w-3.5 h-3.5" />
              Chú thích khoa học & Phân tích vi kiến trúc
            </h4>
            <p className="text-sm italic text-slate-700 mb-2">{caption}</p>
            {analysisText && (
              <p className="text-xs leading-relaxed text-slate-600 border-t border-blue-100 pt-2">
                {analysisText}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

