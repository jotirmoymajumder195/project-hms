# Stub Modules — Future Work

The following modules have complete Prisma schemas but their backend routes are stubs (return `{ data: [] }`) and frontend pages are placeholders:

| Module       | Backend File                              | Frontend Pages                         | What Needs Building                                                    |
|--------------|-------------------------------------------|----------------------------------------|------------------------------------------------------------------------|
| **Lab**      | `modules/lab/lab.routes.js`               | `/lab`                                 | Lab test catalogue CRUD, order placement, sample collection workflow, result entry, report upload (S3), abnormal value flagging |
| **Pharmacy** | `modules/pharmacy/pharmacy.routes.js`     | `/pharmacy`                            | Medicine catalogue, batch management, stock tracking, dispensing from prescription, expiry tracking, reorder alerts |
| **Inventory**| `modules/inventory/inventory.routes.js`   | `/inventory`                           | Stock in/out/adjustment, supplier management, reorder level alerts, transaction history |
| **IPD**      | `modules/ipd/ipd.routes.js`              | `/ipd`                                 | Admission workflow, bed allocation/vacation, daily charge calculation, discharge summary, IPD billing |
| **Notifications** | `modules/notifications/notifications.routes.js` | `/notifications`              | SMS (Twilio), WhatsApp, Email (Nodemailer) integration, notification templates, patient/staff notification preferences, delivery status tracking |

## Lab Module — Schema Ready

Models: `LabTest`, `LabOrder`, `LabOrderItem`
Key fields: test name, code, category, price, normal range, sample type, result, abnormality flag, S3 report URL

## Pharmacy Module — Schema Ready

Models: `Medicine`, `MedicineBatch`, `MedicineDispense`, `MedicineDispenseItem`
Key features: Expiry-aware batch tracking, stock level management, GST/HSN support, dispensing linked to prescriptions

## IPD Module — Schema Ready

Models: `Ward`, `Bed`, `BedAllocation`, `IPDAdmission`
Key features: Ward/bed management, admission/discharge workflow, bed allocation/daily charge, discharge summary

## Daycare Module — Schema Ready

Models: `DaycareAdmission`, `DaycareProcedure`, `DaycareBill`
Key features: Same-day admission for procedures, procedure tracking, billing integration

## Integration Points

- **Lab → Billing**: Lab test costs auto-included in patient bill (same as consumables N03 pattern)
- **Pharmacy → Billing**: Medicine dispensed auto-billed
- **IPD → Billing**: Bed charges + procedures → IPD bill
- **Notifications → All modules**: SMS reminders for appointments, report-ready alerts, bill notifications
