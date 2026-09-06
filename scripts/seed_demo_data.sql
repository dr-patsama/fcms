-- Demo data for testing the live boards (3 patients, today's appointments, OPU, embryos, cryo). Test/dev only.
-- Run: docker exec -i fcms-db psql -U fcms_user fcms_db < scripts/seed_demo_data.sql
DO $$
DECLARE phys uuid; emb uuid; p1 uuid; p2 uuid; p3 uuid; r1 uuid; c1 uuid; o1 uuid; e1 uuid; e2 uuid; today date := (now() at time zone 'Asia/Bangkok')::date;
BEGIN
 SELECT id INTO phys FROM users WHERE role='physician' LIMIT 1;
 SELECT id INTO emb FROM users WHERE role='embryologist' LIMIT 1;
 INSERT INTO patients(id,hn_number,first_name_en,last_name_en,first_name_th,last_name_th,gender) VALUES
  (gen_random_uuid(),'HN-2026-00001','Somying','Jaidee','สมหญิง','ใจดี','female'),
  (gen_random_uuid(),'HN-2026-00002','Malee','Suksan','มาลี','สุขสันต์','female'),
  (gen_random_uuid(),'HN-2026-00003','Nida','Rakdee','นิดา','รักดี','female') ON CONFLICT (hn_number) DO NOTHING;
 SELECT id INTO p1 FROM patients WHERE hn_number='HN-2026-00001'; SELECT id INTO p2 FROM patients WHERE hn_number='HN-2026-00002'; SELECT id INTO p3 FROM patients WHERE hn_number='HN-2026-00003';
 INSERT INTO appointments(id,booking_number,patient_id,appointment_date,appointment_time,appointment_type,appointment_type_th,department,room,provider_id,status,priority,updated_at) VALUES
  (gen_random_uuid(),'BK-2026-00001',p1,today,'08:30','follow_up','ติดตามผล','clinic','Room 1',phys,'checked_in','normal',now()-interval '25 min'),
  (gen_random_uuid(),'BK-2026-00002',p2,today,'09:00','egg_collection','เก็บไข่','operating_room','OR',phys,'in_progress','normal',now()),
  (gen_random_uuid(),'BK-2026-00003',p3,today,'10:30','ultrasound','อัลตราซาวด์','clinic','US Room',phys,'scheduled','normal',now()),
  (gen_random_uuid(),'BK-2026-00004',p1,today,'14:00','embryo_transfer','ย้ายตัวอ่อน','operating_room','OR',phys,'confirmed','urgent',now());
 INSERT INTO treatment_cycles(id,cycle_number,patient_id,cycle_type,start_date,outcome,physician_id,embryologist_id) VALUES (gen_random_uuid(),'CYC-2026-001',p2,'ICSI',today-12,'ongoing',phys,emb) RETURNING id INTO c1;
 INSERT INTO oocyte_retrievals(id,patient_id,cycle_id,procedure_date,start_time,physician_id,embryologist_id,total_follicles_aspirated,total_oocytes_retrieved,mii_count,mi_count,gv_count) VALUES (gen_random_uuid(),p2,c1,today,now()-interval '3 hours',phys,emb,12,9,7,1,1) RETURNING id INTO r1;
 INSERT INTO oocytes(id,retrieval_id,oocyte_number,maturity_stage,is_inseminated,insemination_method,insemination_time) VALUES
  (gen_random_uuid(),r1,1,'MII',true,'ICSI',now()-interval '17 hours'),(gen_random_uuid(),r1,2,'MII',true,'ICSI',now()-interval '17 hours'),(gen_random_uuid(),r1,3,'MII',false,NULL,NULL);
 INSERT INTO embryos(id,embryo_code,patient_id,cycle_id,current_day,created_at) VALUES (gen_random_uuid(),'EMB-2026-001',p3,NULL,3,now()-interval '2 days') RETURNING id INTO e1;
 INSERT INTO embryos(id,embryo_code,patient_id,cycle_id,current_day,created_at) VALUES (gen_random_uuid(),'EMB-2026-002',p3,NULL,3,now()-interval '2 days') RETURNING id INTO e2;
 INSERT INTO embryo_assessments(id,embryo_id,assessment_day,assessment_time,embryologist_id,cell_count,overall_grade) VALUES (gen_random_uuid(),e1,3,now(),emb,8,'8A');
 INSERT INTO embryos(id,embryo_code,patient_id,current_day,disposition,created_at) VALUES (gen_random_uuid(),'EMB-2025-100',p1,5,'frozen',now()-interval '30 days');
 INSERT INTO embryo_cryopreservations(id,embryo_id,embryologist_id,freeze_date,method,device,tank_id,canister,goblet,position) SELECT gen_random_uuid(),id,emb,now()-interval '30 days','vitrification','cryotop','Tank-1','C3','G2','1' FROM embryos WHERE embryo_code='EMB-2025-100';
 INSERT INTO lab_orders(id,order_number,patient_id,ordering_physician_id,lab_type,status,priority) VALUES (gen_random_uuid(),'LO-2026-00001',p1,phys,'general','processing','urgent') ON CONFLICT DO NOTHING;
END $$;
