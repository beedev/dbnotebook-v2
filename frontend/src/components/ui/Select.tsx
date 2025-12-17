import { forwardRef, type SelectHTMLAttributes } from 'react';
import { ChevronDown } from 'lucide-react';

interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectGroup {
  label: string;
  options: SelectOption[];
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  options?: SelectOption[];
  groups?: SelectGroup[];
  placeholder?: string;
  size?: 'sm' | 'md' | 'lg';
  error?: string;
  label?: string;
}

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm pr-8',
  md: 'px-4 py-2 text-base pr-10',
  lg: 'px-5 py-3 text-lg pr-12',
};

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    {
      options = [],
      groups = [],
      placeholder,
      size = 'md',
      error,
      label,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    const hasGroups = groups.length > 0;

    return (
      <div className="relative">
        {label && (
          <label className="block text-sm font-medium text-text-muted mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            disabled={disabled}
            className={`
              w-full appearance-none
              bg-void-light text-text
              border border-void-surface rounded-lg
              font-[family-name:var(--font-body)]
              transition-all duration-200 ease-out
              hover:border-text-dim
              focus:outline-none focus:border-glow focus:ring-1 focus:ring-glow/30
              disabled:opacity-50 disabled:cursor-not-allowed
              ${error ? 'border-danger focus:border-danger focus:ring-danger/30' : ''}
              ${sizeStyles[size]}
              ${className}
            `}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {hasGroups
              ? groups.map((group) => (
                  <optgroup
                    key={group.label}
                    label={group.label}
                    className="bg-void-light text-text"
                  >
                    {group.options.map((option) => (
                      <option
                        key={option.value}
                        value={option.value}
                        disabled={option.disabled}
                        className="bg-void-light text-text"
                      >
                        {option.label}
                      </option>
                    ))}
                  </optgroup>
                ))
              : options.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    disabled={option.disabled}
                    className="bg-void-light text-text"
                  >
                    {option.label}
                  </option>
                ))}
          </select>
          <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <ChevronDown className="w-4 h-4 text-text-muted" />
          </div>
        </div>
        {error && (
          <p className="mt-1 text-sm text-danger">{error}</p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export default Select;
