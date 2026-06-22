import { useEffect, type KeyboardEvent as ReactKeyboardEvent, type MouseEvent as ReactMouseEvent, type ReactNode } from "react";

type PreviewFrameProps = {
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
};

type PreviewOverlayProps = PreviewFrameProps & {
  onClose: () => void;
};

type DevicePagerItem = {
  key: number;
  label: string;
  detail?: string;
};

type DevicePagerProps = {
  label: string;
  items: DevicePagerItem[];
  selectedKey: number;
  onSelect: (key: number) => void;
};

export function PreviewFrame({ title, description, actions, children }: PreviewFrameProps) {
  return (
    <div className="preview-screen">
      <div className="preview-page">
        <header className="page-header">
          <div>
            <p className="eyebrow">Procedure DB / Preview</p>
            <h1>{title}</h1>
            <p>{description}</p>
          </div>
          {actions ? <div className="preview-toolbar">{actions}</div> : null}
        </header>
        {children}
      </div>
    </div>
  );
}

export function PreviewOverlay({ title, description, actions, children, onClose }: PreviewOverlayProps) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  function handleBackdropMouseDown(event: ReactMouseEvent<HTMLDivElement>): void {
    if (event.target === event.currentTarget) {
      onClose();
    }
  }

  function handlePanelKeyDown(event: ReactKeyboardEvent<HTMLElement>): void {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
    }
  }

  return (
    <div className="preview-overlay" role="presentation" onMouseDown={handleBackdropMouseDown}>
      <section
        className="preview-overlay-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="preview-overlay-title"
        onKeyDown={handlePanelKeyDown}
        tabIndex={-1}
      >
        <div className="preview-overlay-shell">
          <header className="page-header preview-overlay-header">
            <div>
              <p className="eyebrow">Procedure DB / Import Preview</p>
              <h1 id="preview-overlay-title">{title}</h1>
              <p>{description}</p>
            </div>
            <div className="preview-toolbar">
              <div className="preview-toolbar-actions">
                {actions}
                <button className="secondary" type="button" onClick={onClose}>
                  <span aria-hidden="true">×</span>
                  閉じる
                </button>
              </div>
            </div>
          </header>
          <div className="preview-overlay-content">{children}</div>
        </div>
      </section>
    </div>
  );
}

export function DevicePager({ label, items, selectedKey, onSelect }: DevicePagerProps) {
  if (items.length <= 1) {
    return null;
  }

  const currentIndex = items.findIndex((item) => item.key === selectedKey);
  const safeIndex = currentIndex >= 0 ? currentIndex : 0;
  const activeItem = items[safeIndex];
  const previousItem = items[safeIndex - 1] ?? null;
  const nextItem = items[safeIndex + 1] ?? null;

  return (
    <section className="device-pager" aria-label={label}>
      <div className="device-pager-summary">
        <span>{label}</span>
        <strong>{activeItem.label}</strong>
        {activeItem.detail ? <small>{activeItem.detail}</small> : null}
      </div>
      <div className="device-pager-actions">
        <button className="secondary" type="button" onClick={() => previousItem && onSelect(previousItem.key)} disabled={!previousItem}>
          <span aria-hidden="true">←</span>
          前
        </button>
        <button className="secondary" type="button" onClick={() => nextItem && onSelect(nextItem.key)} disabled={!nextItem}>
          <span aria-hidden="true">→</span>
          次
        </button>
      </div>
      <div className="device-pager-tabs" role="tablist" aria-label={label}>
        {items.map((item) => (
          <button
            key={item.key}
            className={item.key === selectedKey ? "device-pager-tab active" : "device-pager-tab"}
            type="button"
            role="tab"
            aria-selected={item.key === selectedKey}
            onClick={() => onSelect(item.key)}
          >
            <strong>{item.label}</strong>
            {item.detail ? <span>{item.detail}</span> : null}
          </button>
        ))}
      </div>
    </section>
  );
}
