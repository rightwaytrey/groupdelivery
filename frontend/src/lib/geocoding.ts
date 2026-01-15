import api from './api';
import type { NominatimResult, ParsedAddress, AddressSuggestion } from '../types/geocoding';

/**
 * Parse Nominatim result into structured address fields
 */
function parseNominatimResult(result: NominatimResult): ParsedAddress {
  const addr = result.address;

  // Build street address from components
  const streetParts: string[] = [];
  if (addr.house_number) streetParts.push(addr.house_number);
  if (addr.road) streetParts.push(addr.road);
  const street = streetParts.join(' ') || result.display_name.split(',')[0];

  // Get city from various possible fields
  const city = addr.city || addr.town || addr.village || addr.county || '';

  return {
    street,
    city,
    state: addr.state || '',
    postal_code: addr.postcode || '',
    country: addr.country || 'USA',
    latitude: parseFloat(result.lat),
    longitude: parseFloat(result.lon),
    display_name: result.display_name,
  };
}

/**
 * Search for address suggestions via backend proxy
 */
export async function searchAddresses(
  query: string,
  limit: number = 5
): Promise<AddressSuggestion[]> {
  if (query.length < 3) return [];

  try {
    const response = await api.get<NominatimResult[]>('/geocoding/search', {
      params: { q: query, limit },
    });

    return response.data.map((result) => ({
      id: result.place_id,
      display_name: result.display_name,
      parsed: parseNominatimResult(result),
    }));
  } catch (error) {
    console.error('Address search failed:', error);
    return [];
  }
}
