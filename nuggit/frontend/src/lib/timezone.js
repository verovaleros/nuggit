/**
 * Timezone utilities for consistent datetime handling in the frontend.
 * 
 * This module provides standardized timezone-aware datetime operations
 * to ensure consistent handling of timestamps throughout the frontend.
 */

/**
 * Parse a datetime string into a Date object.
 * Handles various formats commonly used in the application.
 * 
 * @param {string|null|undefined} dateString - The datetime string to parse
 * @returns {Date|null} - Parsed Date object or null if invalid
 */
export function parseDateTime(dateString) {
  if (!dateString) {
    return null;
  }

  try {
    // Handle ISO strings with Z suffix
    if (typeof dateString === 'string' && dateString.endsWith('Z')) {
      return new Date(dateString);
    }
    
    // Handle ISO strings with timezone offset
    if (typeof dateString === 'string' && (dateString.includes('+') || dateString.includes('T'))) {
      return new Date(dateString);
    }
    
    // Handle date-only strings
    if (typeof dateString === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
      return new Date(dateString + 'T00:00:00Z');
    }
    
    // Try parsing as-is
    const date = new Date(dateString);
    
    // Check if the date is valid
    if (isNaN(date.getTime())) {
      console.warn('Invalid date string:', dateString);
      return null;
    }
    
    return date;
  } catch (error) {
    console.error('Error parsing date:', dateString, error);
    return null;
  }
}

/**
 * Format a datetime for human-readable display.
 * 
 * @param {string|Date|null|undefined} dateInput - The datetime to format
 * @param {Object} options - Formatting options
 * @param {boolean} options.includeTime - Whether to include time (default: true)
 * @param {boolean} options.includeTimezone - Whether to include timezone (default: true)
 * @param {string} options.locale - Locale for formatting (default: user's locale)
 * @returns {string} - Formatted datetime string
 */
export function formatDateTime(dateInput, options = {}) {
  const {
    includeTime = true,
    includeTimezone = true,
    locale = undefined
  } = options;

  if (!dateInput) {
    return 'N/A';
  }

  const date = dateInput instanceof Date ? dateInput : parseDateTime(dateInput);
  
  if (!date) {
    return 'Invalid date';
  }

  try {
    const formatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    };

    if (includeTime) {
      formatOptions.hour = '2-digit';
      formatOptions.minute = '2-digit';
      
      if (includeTimezone) {
        formatOptions.timeZoneName = 'short';
      }
    }

    return date.toLocaleDateString(locale, formatOptions);
  } catch (error) {
    console.error('Error formatting date:', dateInput, error);
    return dateInput.toString();
  }
}

/**
 * Format a datetime as relative time (e.g., "2 days ago", "in 3 hours").
 * 
 * @param {string|Date|null|undefined} dateInput - The datetime to format
 * @returns {string} - Relative time string
 */
export function formatRelativeTime(dateInput) {
  if (!dateInput) {
    return 'N/A';
  }

  const date = dateInput instanceof Date ? dateInput : parseDateTime(dateInput);
  
  if (!date) {
    return 'Invalid date';
  }

  try {
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(Math.abs(diffMs) / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    const diffMonth = Math.floor(diffDay / 30);
    const diffYear = Math.floor(diffDay / 365);

    const suffix = diffMs >= 0 ? 'ago' : 'from now';

    if (diffSec < 60) {
      return `${diffSec} second${diffSec !== 1 ? 's' : ''} ${suffix}`;
    } else if (diffMin < 60) {
      return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ${suffix}`;
    } else if (diffHour < 24) {
      return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ${suffix}`;
    } else if (diffDay < 30) {
      return `${diffDay} day${diffDay !== 1 ? 's' : ''} ${suffix}`;
    } else if (diffMonth < 12) {
      return `${diffMonth} month${diffMonth !== 1 ? 's' : ''} ${suffix}`;
    } else {
      return `${diffYear} year${diffYear !== 1 ? 's' : ''} ${suffix}`;
    }
  } catch (error) {
    console.error('Error formatting relative time:', dateInput, error);
    return dateInput.toString();
  }
}

/**
 * Format a datetime with relative time in parentheses.
 * 
 * @param {string|Date|null|undefined} dateInput - The datetime to format
 * @param {Object} options - Formatting options
 * @returns {string} - Formatted datetime with relative time
 */
export function formatDateTimeWithRelative(dateInput, options = {}) {
  if (!dateInput) {
    return 'N/A';
  }

  const formatted = formatDateTime(dateInput, options);
  const relative = formatRelativeTime(dateInput);
  
  if (formatted === 'N/A' || formatted === 'Invalid date') {
    return formatted;
  }
  
  return `${formatted} (${relative})`;
}

/**
 * Format a date for display in tables or compact views.
 * 
 * @param {string|Date|null|undefined} dateInput - The datetime to format
 * @returns {string} - Compact formatted date
 */
export function formatCompactDate(dateInput) {
  if (!dateInput) {
    return 'N/A';
  }

  const date = dateInput instanceof Date ? dateInput : parseDateTime(dateInput);
  
  if (!date) {
    return 'Invalid date';
  }

  try {
    return date.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch (error) {
    console.error('Error formatting compact date:', dateInput, error);
    return dateInput.toString();
  }
}

/**
 * Get the number of days between two dates.
 * 
 * @param {string|Date} date1 - First date
 * @param {string|Date} date2 - Second date (default: now)
 * @returns {number} - Number of days between dates (positive if date1 is after date2)
 */
export function daysBetween(date1, date2 = new Date()) {
  const d1 = date1 instanceof Date ? date1 : parseDateTime(date1);
  const d2 = date2 instanceof Date ? date2 : parseDateTime(date2);
  
  if (!d1 || !d2) {
    return 0;
  }
  
  const diffTime = d1 - d2;
  return Math.floor(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Check if a date is valid.
 * 
 * @param {string|Date|null|undefined} dateInput - The date to validate
 * @returns {boolean} - True if valid date
 */
export function isValidDate(dateInput) {
  if (!dateInput) {
    return false;
  }
  
  const date = dateInput instanceof Date ? dateInput : parseDateTime(dateInput);
  return date !== null && !isNaN(date.getTime());
}

/**
 * Convert a date to ISO string in UTC.
 * 
 * @param {string|Date|null|undefined} dateInput - The date to convert
 * @returns {string|null} - ISO string in UTC or null if invalid
 */
export function toISOString(dateInput) {
  if (!dateInput) {
    return null;
  }
  
  const date = dateInput instanceof Date ? dateInput : parseDateTime(dateInput);
  
  if (!date) {
    return null;
  }
  
  try {
    return date.toISOString();
  } catch (error) {
    console.error('Error converting to ISO string:', dateInput, error);
    return null;
  }
}

/**
 * Get current UTC time as ISO string.
 * 
 * @returns {string} - Current UTC time as ISO string
 */
export function nowUTC() {
  return new Date().toISOString();
}

/**
 * Format a date for input fields (YYYY-MM-DD format).
 * 
 * @param {string|Date|null|undefined} dateInput - The date to format
 * @returns {string} - Date in YYYY-MM-DD format
 */
export function formatForInput(dateInput) {
  if (!dateInput) {
    return '';
  }
  
  const date = dateInput instanceof Date ? dateInput : parseDateTime(dateInput);
  
  if (!date) {
    return '';
  }
  
  try {
    return date.toISOString().split('T')[0];
  } catch (error) {
    console.error('Error formatting for input:', dateInput, error);
    return '';
  }
}
