/**
 * Currency formatting utility for Indian Rupee (INR - ₹).
 */

export const formatINR = (
  amount: number,
  options?: { minimumFractionDigits?: number; maximumFractionDigits?: number }
): string => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: options?.minimumFractionDigits ?? 2,
    maximumFractionDigits: options?.maximumFractionDigits ?? 2,
  }).format(amount);
};

export const formatCurrency = formatINR;
