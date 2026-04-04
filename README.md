# Soft Eligibility Check Documentation

## Overview

The **Soft Eligibility Tool** enables quick filtering of vehicles for warranty eligibility based on basic rule engine criteria (age and odometer reading) without requiring full-fledged vehicle inspections. This pre-screening approach saves time and cost by identifying ineligible vehicles early in the process.

### Goal & North Star Metric

**Goal**: Save time and cost on vehicles where full-fledged inspection is not required by filtering out ineligibility based on basic rule engine criteria (age and odometer reading)

**Process**: 
- **Input**: Registration number and odometer reading
- **Vehicle Data**: Age fetched via Vehicle API (VAAHAN + DS integration)
- **Filter**: Apply rule engine criteria before inspection

**Key Metrics:**
- **North Star Metric**: Increase in inspection to warranty conversion rate
- **Input Metric**: Number of soft eligibility checks performed
- **Output Metric**: Reduction in unnecessary vehicle inspections
- **Business Impact**: Cost savings on avoided inspections and faster processing time

### Business Objectives

- **Accelerate Sales Process**: Quickly determine preliminary eligibility for extended car warranties
- **Reduce Operational Costs**: Avoid unnecessary vehicle inspections for obviously ineligible vehicles
- **Improve Customer Experience**: Provide indicative pricing early in the customer journey
- **Support Sales Teams**: Enable ground sales operations with preliminary warranty information

---

## Product Specifications

### Feature Location
**Miles App Navigation Path:**
```
Add-ons → Warranty → Soft Eligibility (New Tab)
```

**Context:** This feature complements the existing "Hard Eligibility Check" tab, which requires post-inspection data and generates final warranty quotes.

### Eligibility Criteria
- **Vehicle Age**: ≤ 9 years (calculated from registration year)
- **Odometer Reading**: < 120,000 km
- **Both conditions must be met** for warranty eligibility

---

## Workflow Overview

The following diagrams illustrate the complete warranty eligibility assessment process, showing both Soft and Hard eligibility flows:

### Soft Eligibility Workflow
![Soft Eligibility Workflow](soft_eligibility_1.png)

*Figure 1: Soft Eligibility process flow showing the pre-screening approach using registration number and odometer reading to determine initial warranty eligibility before inspection.*

### Complete Eligibility Assessment Flow
![Complete Eligibility Flow](soft_eligibility_2.png)

*Figure 2: Comprehensive workflow showing the relationship between Soft Eligibility (pre-inspection) and Hard Eligibility (post-inspection) processes, including decision points and outcome paths.*

---

## User Journey & Workflow

### Step 1: Input Collection
**Required Inputs:**
- **Registration Number** (e.g., `HR87C1669`)
- **Odometer Reading** (e.g., `100000` km)

### Step 2: Vehicle Data Retrieval
- Make API call to fetch vehicle metadata
- Extract `variantId` and `regn_year`
- Calculate vehicle age: `Current Year - regn_year`

### Step 3: Eligibility Assessment
**Validation Logic:**
```
IF (Vehicle Age ≤ 9 years) AND (Odometer < 120,000 km)
    THEN → Proceed to pricing
    ELSE → Display ineligibility message
```

### Step 4: Pricing Display (If Eligible)
- Call Warranty Listing API with vehicle parameters
- Display available warranty options with:
  - Product vendor (CWI, ICICI)
  - Price (in INR)
  - Duration (in months)
  - Coverage type (e.g., Standard)

**Important Disclaimer:** *"Pricing is indicative. Final issuance subject to inspection."*

### Step 5: Next Steps
- **Call-to-Action**: "Proceed with Vehicle Inspection"
- **Redirect**: Opens Hard Eligibility Check tab for complete inspection and final warranty processing

---

## Process Flow Integration

### Soft Eligibility → Hard Eligibility Transition

As illustrated in the workflow diagrams above, the Soft Eligibility Tool serves as the first gate in the warranty assessment process:

1. **Pre-Screening Phase (Soft Eligibility)**:
   - Quick validation using basic vehicle data
   - Filters out obviously ineligible vehicles
   - Provides indicative pricing for qualifying vehicles

2. **Detailed Assessment Phase (Hard Eligibility)**:
   - Comprehensive vehicle inspection required
   - Final warranty pricing and terms
   - Actual policy issuance

This two-stage approach optimizes resource allocation by ensuring only potentially eligible vehicles proceed to the more expensive inspection phase.

---

## API Specifications

### 1. Vehicle Metadata API

**Endpoint:**
```
GET https://vehicle.cars24.team/v6/vehicle-number/{registrationNumber}
```

**Headers:**
```
origin_source: B2C_VAS
platform: B2C
device_category: mSite
```

**Authentication:**
- **Type**: Basic Auth
- **Username**: `B2C_VAS`
- **Password**: `64eb8951fdb5844aafaeff9e7e410c3d14ba97ca`

**Sample Request:**
```bash
curl --location 'https://vehicle.cars24.team/v6/vehicle-number/HR87C1669' \
--header 'origin_source: B2C_VAS' \
--header 'platform: B2C' \
--header 'device_category: mSite'
```

**Response Schema:**
```json
{
  "regn_year": 2019,
  "variantId": 8559,
  "status": "success",
  "message": "Vehicle found"
}
```

**Key Response Fields:**
- `regn_year`: Registration year used for age calculation
- `variantId`: Required for warranty pricing API

### 2. Warranty Pricing API (v2)

**Endpoint:**
```
GET https://b2c-oms-india.c24.tech/api/v1/warranty/offline-sales/pricing
```

**Query Parameters:**
- `variantId`: Vehicle variant identifier
- `carAge`: Calculated vehicle age in years
- `odometer`: Odometer reading in kilometers

**Headers:**
```
x-client-id: 25239
Authorization: Bearer OOZLKMGZTOGXFGEGDWBQ79KYT3LYBFPK9IRX5W
Cookie: __cf_bm=wnRubK8MOxlU.vCjH7iYnYQIPgbEStg5chZ697LwOhM-1748420218-1.0.1.1-ILLE_V0gNJQakIKuV2p_KigJCr2bkeuFy.g_b_fpjzh1oFSdghz8pJ4DIvlz6gVdz5PbBBecaB.lXJ0ZjYPUnlhZKVlL4eK_pDzrx7bxIks
```

**Sample Request:**
```bash
curl --location 'https://b2c-oms-india.c24.tech/api/v1/warranty/offline-sales/pricing?variantId=8559&carAge=3&odometer=100000' \
--header 'x-client-id: 25239' \
--header 'Authorization: Bearer OOZLKMGZTOGXFGEGDWBQ79KYT3LYBFPK9IRX5W' \
--header 'Cookie: __cf_bm=wnRubK8MOxlU.vCjH7iYnYQIPgbEStg5chZ697LwOhM-1748420218-1.0.1.1-ILLE_V0gNJQakIKuV2p_KigJCr2bkeuFy.g_b_fpjzh1oFSdghz8pJ4DIvlz6gVdz5PbBBecaB.lXJ0ZjYPUnlhZKVlL4eK_pDzrx7bxIks'
```

**Response Schema:**
```json
[
  {
    "vendor": "ICICI",
    "price": 5000.0,
    "coverage": "Standard",
    "durationInMonths": "12"
  },
  {
    "vendor": "CWI",
    "price": 6500.0,
    "coverage": "Standard",
    "durationInMonths": "12"
  }
]
```

---

## Edge Cases

### Vehicle Not Found
**Scenario**: Invalid registration number or vehicle not in database
**Response**: 
- **Invalid Registration**: "Invalid registration number, retry with a valid registration number"
- **Vehicle Not in Database**: "Details could not be fetched, please proceed with inspection"

### Ineligible Vehicle
**Scenario**: Vehicle fails age or odometer criteria
**Response**: 
- Clear explanation of ineligibility reasons:
  - **Age Exceeded**: "Vehicle is over 9 years old and not eligible for warranty"
  - **High Mileage**: "Vehicle has exceeded 120,000 km and not eligible for warranty"
  - **Both Criteria Failed**: "Vehicle exceeds both age (9 years) and mileage (120,000 km) limits"

### API Failures
**Scenario**: Service unavailability or timeout
**Response**: 
- "Service temporarily unavailable, please try again in a few moments"

---

## Technical Considerations

### Performance Requirements
- **Response Time**: < 3 seconds for complete eligibility check workflow
- **Availability**: 99.9% uptime during business hours (9 AM - 9 PM IST)
- **Concurrent Users**: Support up to 1000 simultaneous requests
- **Error Rate**: < 1% for successful API responses

### Data Privacy & Security
- **PII Handling**: Registration numbers should be handled securely
- **Logging**: Implement comprehensive logging for debugging and monitoring

### Monitoring & Analytics
- **Success Rate**: Track successful soft eligibility assessments
- **Conversion Funnel**: Monitor progression from soft eligibility → inspection → warranty sale
- **Performance Metrics**: API response times and system availability
- **Business Impact**: Track reduction in unnecessary inspections and improvement in conversion rates

---

## Implementation Notes

### Version Differences
- **v1 vs v2**: This implementation uses Warranty Listing API v2, which provides simplified pricing without component-level metadata
- **Pre-inspection Focus**: No `app_id` required as this is purely pre-inspection assessment

### Future Enhancements
- **Caching**: Implement vehicle data caching for frequently checked vehicles
- **Batch Processing**: Support multiple vehicle checks in a single request
- **Enhanced Filtering**: Additional filter options for warranty products

### Dependencies
- Vehicle API service availability
- Warranty pricing service availability
- Miles App integration points

---

*Last Updated: [Date]*
*Version: 1.1*
*Document Owner: [Product Manager Name]*