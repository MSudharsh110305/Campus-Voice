import React from 'react';

/**
 * EliteButton - Premium button for Admin / Authority dashboards.
 * SREC forest-green + warm-gold theme.
 *
 * Variants: primary · secondary · success · warning · danger · outline · ghost
 * Sizes:    sm · md · lg · icon
 */
const EliteButton = ({
    children,
    variant = 'primary',
    size = 'md',
    className = '',
    isLoading = false,
    disabled = false,
    ...props
}) => {

    const baseStyles = [
        'rounded-xl font-semibold transition-all duration-200 will-change-transform',
        'flex items-center justify-center gap-2',
        'focus:outline-none focus:ring-2 focus:ring-offset-2',
        'active:scale-[0.97] active:translate-y-0',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none disabled:scale-100',
    ].join(' ');

    const sizes = {
        sm:   'px-3 py-1.5 text-xs',
        md:   'px-5 py-2.5 text-sm',
        lg:   'px-6 py-3 text-base',
        icon: 'p-2 w-9 h-9 items-center justify-center flex',
    };

    const variants = {
        primary:
            'bg-srec-primary text-white border border-srec-primary/80 shadow-btn-primary hover:bg-srec-primaryHover hover:shadow-btn-primary-hover hover:-translate-y-px focus:ring-srec-primary/40',

        secondary:
            'bg-white text-srec-primary border border-srec-primary/40 shadow-btn hover:bg-srec-primarySoft hover:border-srec-primaryMuted hover:shadow-btn-hover hover:-translate-y-px focus:ring-srec-primary/30',

        success:
            'bg-srec-primaryLight text-white border border-srec-primaryLight/80 shadow-btn-primary hover:bg-green-500 hover:shadow-btn-primary-hover hover:-translate-y-px focus:ring-green-400/40',

        warning:
            'bg-srec-gold text-white border border-srec-gold/70 shadow-btn hover:bg-srec-goldMuted hover:shadow-btn-hover hover:-translate-y-px focus:ring-srec-gold/40',

        danger:
            'bg-srec-danger text-white border border-srec-danger/80 shadow-btn-danger hover:bg-srec-dangerDark hover:shadow-btn-danger-hover hover:-translate-y-px focus:ring-srec-danger/40',

        outline:
            'bg-white text-srec-primary border border-srec-border shadow-btn hover:bg-srec-backgroundAlt hover:border-srec-primaryMuted hover:shadow-btn-hover hover:-translate-y-px focus:ring-srec-primary/30',

        ghost:
            'bg-transparent text-srec-textMuted border border-transparent shadow-none hover:bg-srec-backgroundAlt hover:text-srec-textPrimary focus:ring-srec-primary/20',
    };

    const finalClassName = [
        baseStyles,
        sizes[size] ?? sizes.md,
        variants[variant] ?? variants.primary,
        className,
    ].join(' ');

    return (
        <button
            className={finalClassName}
            disabled={disabled || isLoading}
            {...props}
        >
            {isLoading ? (
                <>
                    <svg className="animate-spin h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Loading…
                </>
            ) : children}
        </button>
    );
};

export default EliteButton;
