# Plan: Add Delivery Window UI to Addresses

## Summary
Add time input fields to the AddressForm component to allow users to set delivery time windows using the existing `preferred_time_start` and `preferred_time_end` backend fields.

## Requirements
- Labels: "No Deliveries Before:" and "No Deliveries After:"
- Optional fields - empty means no time restriction (current behavior preserved)
- Time format: HH:MM (24-hour format, matches existing backend validation)

## Files to Modify

### 1. `frontend/src/components/AddressForm.tsx`
Add two time input fields:
- `preferred_time_start` - labeled "No Deliveries Before:"
- `preferred_time_end` - labeled "No Deliveries After:"

Implementation:
- Add HTML `<input type="time">` elements
- Place in a row together (similar to city/state layout)
- Position after phone/before notes section
- Both fields optional, no validation needed (backend handles it)

### 2. `frontend/src/pages/Addresses.tsx` (optional enhancement)
Consider displaying delivery window in the addresses table:
- Add column or show in address details
- Format: show time range if set, otherwise show "-" or "Any time"

## Implementation Steps

1. **Edit AddressForm.tsx:**
   - Add time inputs with labels "No Deliveries Before:" and "No Deliveries After:"
   - Wire to formData.preferred_time_start and formData.preferred_time_end
   - Style consistently with existing form fields

2. **Edit Addresses.tsx:**
   - Add delivery window display to the table (optional column or tooltip)

## Verification
1. Start the frontend dev server
2. Create a new address with delivery window times set
3. Verify times are saved and displayed correctly
4. Edit an existing address, verify times load and can be modified
5. Create address without times, verify no restrictions applied
