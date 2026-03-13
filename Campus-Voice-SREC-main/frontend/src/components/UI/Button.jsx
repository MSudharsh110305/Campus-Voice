import React from 'react';

export default function Button({
    children,
    variant = "primary",
    className = "",
    isLoading = false,
    ...props
}) {
    const variants = {
        primary:
            "bg-srec-primary hover:bg-srec-primaryHover text-white border border-srec-primary/80 shadow-btn-primary hover:shadow-btn-primary-hover hover:-translate-y-px active:translate-y-0 active:shadow-inner-soft disabled:opacity-70 disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0",

        secondary:
            "bg-white border border-srec-border text-srec-textPrimary shadow-btn hover:shadow-btn-hover hover:-translate-y-px hover:border-srec-borderHover active:translate-y-0 active:shadow-inner-soft disabled:opacity-70 disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0",

        gold:
            "bg-srec-gold hover:bg-srec-goldMuted text-white border border-srec-gold/70 shadow-btn hover:shadow-btn-hover hover:-translate-y-px active:translate-y-0 active:shadow-inner-soft disabled:opacity-70 disabled:cursor-not-allowed",

        danger:
            "bg-srec-danger hover:bg-srec-dangerDark text-white border border-srec-danger/80 shadow-btn-danger hover:shadow-btn-danger-hover hover:-translate-y-px active:translate-y-0 active:shadow-inner-soft disabled:opacity-70 disabled:cursor-not-allowed disabled:shadow-none disabled:translate-y-0",

        ghost:
            "text-srec-primary hover:bg-srec-primarySoft border border-transparent hover:border-srec-primaryMuted/30 disabled:opacity-70 disabled:cursor-not-allowed",
    };

    return (
        <button
            className={`
        px-5 py-2.5
        rounded-xl
        font-semibold text-sm
        transition-all duration-200
        will-change-transform
        focus:outline-none focus:ring-2 focus:ring-srec-primary/40 focus:ring-offset-2
        flex items-center justify-center gap-2
        ${variants[variant]}
        ${className}
      `}
            disabled={isLoading || props.disabled}
            {...props}
        >
            {isLoading && (
                <svg className="animate-spin h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            )}
            {children}
        </button>
    );
}
