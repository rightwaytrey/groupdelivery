import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { useDebounce } from '../hooks/useDebounce';
import { searchAddresses } from '../lib/geocoding';
import type { AddressSuggestion, ParsedAddress } from '../types/geocoding';

interface AddressAutocompleteProps {
  // For AddressForm: populate individual fields
  onSelectParsed?: (address: ParsedAddress) => void;
  // For DriverForm: just get the display string
  onSelectString?: (displayName: string) => void;
  // Initial value for the input
  initialValue?: string;
  // Label text
  label: string;
  // Whether field is required
  required?: boolean;
  // Placeholder text
  placeholder?: string;
  // Additional CSS classes for the input
  className?: string;
  // ID for the input element
  id?: string;
  // Clear input after selection (useful for search-only fields)
  clearOnSelect?: boolean;
}

export default function AddressAutocomplete({
  onSelectParsed,
  onSelectString,
  initialValue = '',
  label,
  required = false,
  placeholder = 'Start typing an address...',
  className = '',
  id = 'address-autocomplete',
  clearOnSelect = false,
}: AddressAutocompleteProps) {
  const [inputValue, setInputValue] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Debounce search query (300ms delay respects Nominatim rate limits)
  const debouncedQuery = useDebounce(inputValue, 300);

  // Update input when initialValue changes (for edit mode)
  useEffect(() => {
    setInputValue(initialValue);
  }, [initialValue]);

  // Fetch suggestions when debounced query changes
  useEffect(() => {
    const fetchSuggestions = async () => {
      if (debouncedQuery.length < 3) {
        setSuggestions([]);
        setIsOpen(false);
        return;
      }

      setIsLoading(true);
      try {
        const results = await searchAddresses(debouncedQuery);
        setSuggestions(results);
        setIsOpen(results.length > 0);
        setHighlightedIndex(-1);
      } catch (error) {
        console.error('Failed to fetch suggestions:', error);
        setSuggestions([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSuggestions();
  }, [debouncedQuery]);

  // Handle selection of a suggestion
  const handleSelect = (suggestion: AddressSuggestion) => {
    setInputValue(clearOnSelect ? '' : suggestion.display_name);
    setIsOpen(false);
    setSuggestions([]);

    if (onSelectParsed) {
      onSelectParsed(suggestion.parsed);
    }
    if (onSelectString) {
      onSelectString(suggestion.display_name);
    }
  };

  // Keyboard navigation
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
          handleSelect(suggestions[highlightedIndex]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setHighlightedIndex(-1);
        break;
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        inputRef.current &&
        !inputRef.current.contains(event.target as Node) &&
        listRef.current &&
        !listRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const highlightedElement = listRef.current.children[highlightedIndex] as HTMLElement;
      highlightedElement?.scrollIntoView({ block: 'nearest' });
    }
  }, [highlightedIndex]);

  return (
    <div className="relative">
      <label htmlFor={id} className="block text-sm font-medium text-gray-700">
        {label} {required && '*'}
      </label>

      <div className="relative mt-1">
        <input
          ref={inputRef}
          type="text"
          id={id}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setIsOpen(true)}
          placeholder={placeholder}
          required={required}
          autoComplete="off"
          className={`block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border ${className}`}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
          aria-controls={`${id}-listbox`}
          role="combobox"
        />

        {/* Loading indicator */}
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <svg
              className="animate-spin h-4 w-4 text-gray-400"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Suggestions dropdown */}
      {isOpen && suggestions.length > 0 && (
        <ul
          ref={listRef}
          id={`${id}-listbox`}
          role="listbox"
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm"
        >
          {suggestions.map((suggestion, index) => (
            <li
              key={suggestion.id}
              role="option"
              aria-selected={index === highlightedIndex}
              onClick={() => handleSelect(suggestion)}
              onMouseEnter={() => setHighlightedIndex(index)}
              className={`relative cursor-pointer select-none py-2 px-3 ${
                index === highlightedIndex
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-900 hover:bg-gray-100'
              }`}
            >
              <span className="block truncate">{suggestion.display_name}</span>
            </li>
          ))}
        </ul>
      )}

      {/* No results message */}
      {isOpen && !isLoading && suggestions.length === 0 && inputValue.length >= 3 && (
        <div className="absolute z-50 mt-1 w-full rounded-md bg-white py-2 px-3 text-sm text-gray-500 shadow-lg ring-1 ring-black ring-opacity-5">
          No addresses found
        </div>
      )}
    </div>
  );
}
