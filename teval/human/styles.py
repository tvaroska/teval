"""
CSS styles for the human evaluation interface.

This module provides CSS styles for the evaluation forms,
ensuring a clean, responsive, and accessible design.
"""


def get_styles() -> str:
    """
    Get CSS styles for the evaluation interface.

    Returns
    -------
    str
        Complete CSS stylesheet as a string.

    Notes
    -----
    The styles provide:
    - Mobile-responsive design using flexbox
    - Dark mode support via CSS variables
    - Accessible color contrast ratios
    - Smooth transitions and hover effects
    - Print-friendly styles
    """
    return """
    /* CSS Variables for theming */
    :root {
        --teval-primary: #2563eb;
        --teval-primary-hover: #1d4ed8;
        --teval-secondary: #64748b;
        --teval-secondary-hover: #475569;
        --teval-success: #10b981;
        --teval-error: #ef4444;
        --teval-warning: #f59e0b;
        --teval-bg: #ffffff;
        --teval-bg-secondary: #f8fafc;
        --teval-border: #e2e8f0;
        --teval-text: #1e293b;
        --teval-text-secondary: #64748b;
        --teval-shadow: rgba(0, 0, 0, 0.1);
        --teval-radius: 0.5rem;
    }

    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        :root {
            --teval-bg: #0f172a;
            --teval-bg-secondary: #1e293b;
            --teval-border: #334155;
            --teval-text: #f1f5f9;
            --teval-text-secondary: #94a3b8;
            --teval-shadow: rgba(0, 0, 0, 0.3);
        }
    }

    /* Container and layout */
    .teval-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 2rem;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        color: var(--teval-text);
        background-color: var(--teval-bg);
        min-height: 100vh;
    }

    .teval-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 2rem;
        color: var(--teval-text);
        text-align: center;
    }

    /* Form styles */
    .teval-form {
        background-color: var(--teval-bg);
        padding: 1rem;
    }

    /* Filter bar */
    .teval-filter-bar {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
        padding: 1rem;
        background-color: var(--teval-bg-secondary);
        border-radius: var(--teval-radius);
        flex-wrap: wrap;
        align-items: center;
    }

    .teval-search {
        flex: 1;
        min-width: 200px;
        padding: 0.5rem 1rem;
        border: 1px solid var(--teval-border);
        border-radius: var(--teval-radius);
        background-color: var(--teval-bg);
        color: var(--teval-text);
        font-size: 1rem;
    }

    .teval-filter-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        font-size: 0.875rem;
        color: var(--teval-text-secondary);
    }

    /* Section styles */
    .teval-section {
        margin-bottom: 2rem;
    }

    .teval-section-title {
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: var(--teval-text);
    }

    .teval-section-desc {
        color: var(--teval-text-secondary);
        margin-bottom: 1rem;
        font-size: 0.875rem;
    }

    /* Metric card styles */
    .teval-metric-card {
        background-color: var(--teval-bg-secondary);
        border: 1px solid var(--teval-border);
        border-radius: var(--teval-radius);
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: box-shadow 0.2s ease;
    }

    .teval-metric-card:hover {
        box-shadow: 0 4px 6px var(--teval-shadow);
    }

    .teval-metric-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
    }

    .teval-metric-id {
        font-weight: 600;
        font-size: 1rem;
        color: var(--teval-text);
    }

    .teval-badge-mandatory {
        background-color: var(--teval-error);
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }

    .teval-metric-rubric {
        color: var(--teval-text);
        margin-bottom: 1rem;
        line-height: 1.5;
    }

    .teval-metric-inputs {
        display: flex;
        gap: 2rem;
        margin-bottom: 1rem;
    }

    .teval-radio {
        display: flex;
        align-items: center;
        cursor: pointer;
    }

    .teval-radio input[type="radio"] {
        margin-right: 0.5rem;
        width: 1.25rem;
        height: 1.25rem;
        cursor: pointer;
    }

    .teval-radio-label {
        font-size: 1rem;
        color: var(--teval-text);
        user-select: none;
    }

    .teval-reasoning {
        width: 100%;
        padding: 0.75rem;
        border: 1px solid var(--teval-border);
        border-radius: var(--teval-radius);
        background-color: var(--teval-bg);
        color: var(--teval-text);
        font-size: 0.875rem;
        font-family: inherit;
        resize: vertical;
        min-height: 80px;
    }

    .teval-reasoning:focus {
        outline: none;
        border-color: var(--teval-primary);
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }

    /* Progress indicator */
    .teval-progress-container {
        margin: 2rem 0;
        padding: 1rem;
        background-color: var(--teval-bg-secondary);
        border-radius: var(--teval-radius);
    }

    .teval-progress-text {
        display: block;
        margin-bottom: 0.5rem;
        font-size: 0.875rem;
        color: var(--teval-text-secondary);
    }

    .teval-progress {
        width: 100%;
        height: 0.5rem;
        border-radius: 0.25rem;
        background-color: var(--teval-border);
    }

    .teval-progress::-webkit-progress-value {
        background-color: var(--teval-primary);
        border-radius: 0.25rem;
        transition: width 0.3s ease;
    }

    .teval-progress::-moz-progress-bar {
        background-color: var(--teval-primary);
        border-radius: 0.25rem;
        transition: width 0.3s ease;
    }

    /* Action buttons */
    .teval-actions {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-top: 2rem;
    }

    .teval-btn-primary,
    .teval-btn-secondary {
        padding: 0.75rem 1.5rem;
        border-radius: var(--teval-radius);
        font-size: 1rem;
        font-weight: 500;
        border: none;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: center;
    }

    .teval-btn-primary {
        background-color: var(--teval-primary);
        color: white;
    }

    .teval-btn-primary:hover:not(:disabled) {
        background-color: var(--teval-primary-hover);
        box-shadow: 0 4px 6px var(--teval-shadow);
    }

    .teval-btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .teval-btn-secondary {
        background-color: var(--teval-secondary);
        color: white;
    }

    .teval-btn-secondary:hover {
        background-color: var(--teval-secondary-hover);
        box-shadow: 0 4px 6px var(--teval-shadow);
    }

    .teval-autosave-on {
        background-color: var(--teval-success);
    }

    .teval-autosave-off {
        background-color: var(--teval-secondary);
    }

    /* Results display */
    .teval-result-container {
        margin-top: 2rem;
    }

    .teval-result {
        padding: 2rem;
        background-color: var(--teval-bg-secondary);
        border-radius: var(--teval-radius);
        border: 1px solid var(--teval-border);
    }

    .teval-result h3 {
        font-size: 1.5rem;
        margin-bottom: 1rem;
    }

    .teval-result-success {
        color: var(--teval-success);
    }

    .teval-result-fail {
        color: var(--teval-error);
    }

    .teval-result p {
        color: var(--teval-text);
        margin-bottom: 0.5rem;
    }

    .teval-error {
        border-color: var(--teval-error);
        background-color: rgba(239, 68, 68, 0.1);
    }

    /* Mobile responsive */
    @media (max-width: 640px) {
        .teval-container {
            padding: 1rem;
        }

        .teval-title {
            font-size: 1.5rem;
        }

        .teval-metric-inputs {
            flex-direction: column;
            gap: 1rem;
        }

        .teval-actions {
            flex-direction: column;
        }

        .teval-btn-primary,
        .teval-btn-secondary {
            width: 100%;
        }

        .teval-filter-bar {
            flex-direction: column;
            align-items: stretch;
        }

        .teval-search {
            width: 100%;
        }
    }

    /* Print styles */
    @media print {
        .teval-filter-bar,
        .teval-actions,
        .teval-progress-container {
            display: none;
        }

        .teval-container {
            max-width: 100%;
            padding: 0;
        }

        .teval-metric-card {
            page-break-inside: avoid;
            border: 1px solid #000;
            margin-bottom: 0.5rem;
            padding: 0.5rem;
        }
    }

    /* Animations */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .teval-result {
        animation: slideIn 0.3s ease;
    }

    /* Focus styles for accessibility */
    *:focus-visible {
        outline: 2px solid var(--teval-primary);
        outline-offset: 2px;
    }

    /* Toast notifications (for auto-save) */
    .teval-toast {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background-color: var(--teval-success);
        color: white;
        border-radius: var(--teval-radius);
        box-shadow: 0 4px 6px var(--teval-shadow);
        animation: slideIn 0.3s ease;
        z-index: 1000;
    }
    """