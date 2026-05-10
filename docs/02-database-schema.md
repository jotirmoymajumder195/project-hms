# Database Schema

**Database**: PostgreSQL, ORM: Prisma 5

## Enums

| Enum                | Values                                                                 |
|---------------------|------------------------------------------------------------------------|
| Role                | ADMIN, RECEPTION, DOCTOR, LAB, PHARMACIST, PATIENT, DISPLAY            |
| Gender              | MALE, FEMALE, OTHER, PREFER_NOT_TO_SAY                                 |
| BloodGroup          | A_POS, A_NEG, B_POS, B_NEG, AB_POS, AB_NEG, O_POS, O_NEG, UNKNOWN     |
| AppointmentStatus   | SCHEDULED, CHECKED_IN, IN_CONSULTATION, COMPLETED, CANCELLED, NO_SHOW  |
| VisitType           | OPD, EMERGENCY, FOLLOW_UP                                              |
| PaymentStatus       | PENDING, PARTIALLY_PAID, PAID, REFUNDED, WAIVED                        |
| PaymentMethod       | CASH, CARD, UPI, NETBANKING, INSURANCE, TPA                            |
| LabOrderStatus      | ORDERED, SAMPLE_COLLECTED, PROCESSING, COMPLETED, CANCELLED            |
| IPDStatus           | ADMITTED, DISCHARGED, TRANSFERRED, DECEASED                            |
| BedStatus           | AVAILABLE, OCCUPIED, UNDER_MAINTENANCE, RESERVED                       |
| BedType             | GENERAL, SEMI_PRIVATE, PRIVATE, ICU, NICU, HDU                         |
| NotificationType    | APPOINTMENT_REMINDER, REPORT_READY, BILL_GENERATED, DISCHARGE_SUMMARY, LOW_STOCK_ALERT, GENERAL |
| NotificationChannel | SMS, WHATSAPP, EMAIL, IN_APP                                           |
| AuditAction         | CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, PRINT             |
| ConsentPurpose      | DATA_COLLECTION, TREATMENT, SHARING_LAB, MARKETING                     |
| DataRequestType     | EXPORT, DELETION, CORRECTION                                           |
| DataRequestStatus   | PENDING, IN_PROGRESS, COMPLETED, REJECTED                              |
| DaycareStatus       | ADMITTED, PROCEDURE_IN_PROGRESS, PROCEDURE_DONE, DISCHARGED, CANCELLED |

## Models (30+)

### Users & Auth
- **User** — Staff login accounts (id, name, email, phone, passwordHash, role, isActive, mustChangePassword, lastLoginAt)

### DPDPA 2023 Compliance
- **ConsentLog** — Patient consent records (patientId, purpose, consentGiven, consentText, collectedBy)
- **DataRequest** — Patient data export/deletion requests (type, status, reason)
- **AuditLog** — Every action logged (userId, action, resource, resourceId, details JSON, ipAddress)

### Patient Management
- **Patient** — Patient records (uhid, name, phone, aadhaarEncrypted, abhaNumber, etc.)

### Doctor Management
- **Doctor** — Doctor profiles linked to User (specialization, qualification, consultationFee, isOPD/isEmergency/isIPD)
- **DoctorSchedule** — Weekly time slots per doctor (dayOfWeek, startTime, endTime, slotMinutes, scheduleType)

### Appointments & Queue
- **Appointment** — Booked/walk-in slots (patientId, doctorId, appointmentDate, slotTime, tokenNumber, status, isWalkIn, skippedAt)
- **DoctorQueue** — Current queue state per doctor (currentToken, currentVisitId, chamberId, isActive)

### OPD
- **OPDRegistration** — One per patient lifetime (opdNumber like OPD-2026-00001)
- **OPDVisit** — Each consultation visit (chiefComplaint, vitalSigns JSON, diagnosis, icdCode, followUpDate, awaitingCompletion)
- **Prescription** — Doctor's prescription per visit
- **PrescriptionMedicine** — Individual medicines (name, dosage, frequency, duration)

### Consumables
- **Consumable** — Catalogue (name, category, unit, unitPrice)
- **VisitConsumable** — Consumables used during a visit (snapshot price)

### Billing
- **Bill** — Bills per visit (billNumber, subtotal, discount, totalAmount, paidAmount, balanceAmount, paymentStatus)
- **BillItem** — Line items (itemType, itemName, quantity, unitPrice)
- **Payment** — Payment records (amount, method, transactionRef)

### Lab
- **LabTest** — Test catalogue (name, code, category, price, normalRange)
- **LabOrder** — Orders per patient/visit
- **LabOrderItem** — Individual test results

### Pharmacy
- **Medicine** — Drug catalogue (name, genericName, category, unitPrice, mrp, currentStock, reorderLevel)
- **MedicineBatch** — Stock batches (batchNumber, expiryDate, quantity)
- **MedicineDispense** — Patient dispensing events
- **MedicineDispenseItem** — Dispensed items

### Inventory
- **InventoryItem** — Non-medicine stock items
- **InventoryTransaction** — Stock movements (IN, OUT, ADJUSTMENT)

### IPD
- **Ward** — Wards (name, floor, totalBeds)
- **Bed** — Individual beds (bedNumber, bedType, dailyCharge, status)
- **IPDAdmission** — Admissions (admissionNumber, diagnosis, status)
- **BedAllocation** — Bed assignments

### Daycare
- **DaycareAdmission** — Same-day procedures (daycareNumber, plannedProcedure, status)
- **DaycareProcedure** — Procedure records
- **DaycareBill** — Link to bills

### OPD Chambers
- **OPDChamber** — Physical consultation rooms
- **OPDChamberAssignment** — Doctor-to-chamber assignments (one-off or recurring)

### Notifications & Settings
- **Notification** — Outbound notification log
- **HospitalSettings** — Hospital info, GST, branding
