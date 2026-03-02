"""
FCMS Module 2 - Lab Service
Business logic for General Lab, Embryology, Andrology
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
import uuid

from ..models.lab_models import (
    LabOrder, LabOrderItem, LabSpecimen, LabResult, LabTestPanel,
    TreatmentCycle, OocyteRetrieval, Oocyte, FertilizationRecord,
    Embryo, EmbryoAssessment, EmbryoCryopreservation, EmbryoWarming,
    EmbryoTransfer, SemenAnalysis, SpermPreparation, SpermCryopreservation,
    OrderStatus, ResultFlag, FertilizationStatus, EmbryoDisposition
)
from ..schemas.lab_schemas import (
    LabOrderCreate, LabResultCreate, SpecimenCreate,
    TreatmentCycleCreate, OocyteRetrievalCreate,
    EmbryoAssessmentCreate, EmbryoCryoCreate,
    EmbryoWarmingCreate, EmbryoTransferCreate,
    SemenAnalysisCreate
)


class LabService:
    def __init__(self, db: Session):
        self.db = db

    # ─── SEQUENCE GENERATORS ────────────────────────────────

    def _next_order_number(self) -> str:
        year = datetime.now().year
        last = self.db.query(LabOrder).filter(
            LabOrder.order_number.like(f"LO-{year}-%")
        ).order_by(desc(LabOrder.order_number)).first()
        seq = 1
        if last:
            seq = int(last.order_number.split("-")[-1]) + 1
        return f"LO-{year}-{seq:05d}"

    def _next_cycle_number(self) -> str:
        year = datetime.now().year
        last = self.db.query(TreatmentCycle).filter(
            TreatmentCycle.cycle_number.like(f"CYC-{year}-%")
        ).order_by(desc(TreatmentCycle.cycle_number)).first()
        seq = 1
        if last:
            seq = int(last.cycle_number.split("-")[-1]) + 1
        return f"CYC-{year}-{seq:04d}"

    def _next_embryo_code(self) -> str:
        year = datetime.now().year
        last = self.db.query(Embryo).filter(
            Embryo.embryo_code.like(f"EMB-{year}-%")
        ).order_by(desc(Embryo.embryo_code)).first()
        seq = 1
        if last:
            seq = int(last.embryo_code.split("-")[-1]) + 1
        return f"EMB-{year}-{seq:04d}"

    def _next_barcode(self) -> str:
        return f"SP-{uuid.uuid4().hex[:10].upper()}"

    def _next_sa_number(self) -> str:
        year = datetime.now().year
        last = self.db.query(SemenAnalysis).filter(
            SemenAnalysis.analysis_number.like(f"SA-{year}-%")
        ).order_by(desc(SemenAnalysis.analysis_number)).first()
        seq = 1
        if last:
            seq = int(last.analysis_number.split("-")[-1]) + 1
        return f"SA-{year}-{seq:04d}"

    # ─── GENERAL LAB ────────────────────────────────────────

    async def create_order(self, data: LabOrderCreate, user_id: str) -> LabOrder:
        order = LabOrder(
            order_number=self._next_order_number(),
            patient_id=str(data.patient_id),
            visit_id=str(data.visit_id) if data.visit_id else None,
            ordering_physician_id=user_id,
            lab_type=data.lab_type,
            priority=data.priority,
            clinical_notes=data.clinical_notes,
            diagnosis_code=data.diagnosis_code,
            status=OrderStatus.PENDING
        )
        self.db.add(order)
        self.db.flush()

        for panel_id in data.test_panel_ids:
            item = LabOrderItem(
                order_id=order.id,
                test_panel_id=str(panel_id),
                status=OrderStatus.PENDING
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(order)
        return order

    async def list_orders(
        self, patient_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        lab_type: Optional[str] = None
    ) -> List[LabOrder]:
        q = self.db.query(LabOrder).options(
            joinedload(LabOrder.items).joinedload(LabOrderItem.test_panel),
            joinedload(LabOrder.items).joinedload(LabOrderItem.result)
        )
        if patient_id:
            q = q.filter(LabOrder.patient_id == str(patient_id))
        if status:
            q = q.filter(LabOrder.status == status)
        if lab_type:
            q = q.filter(LabOrder.lab_type == lab_type)
        return q.order_by(desc(LabOrder.ordered_at)).all()

    async def get_order(self, order_id: uuid.UUID) -> Optional[LabOrder]:
        return self.db.query(LabOrder).options(
            joinedload(LabOrder.items).joinedload(LabOrderItem.test_panel),
            joinedload(LabOrder.items).joinedload(LabOrderItem.result),
            joinedload(LabOrder.specimens)
        ).filter(LabOrder.id == str(order_id)).first()

    async def update_order_status(self, order_id: uuid.UUID, new_status: str, user_id: str):
        order = self.db.query(LabOrder).filter(LabOrder.id == str(order_id)).first()
        if not order:
            raise ValueError("Order not found")

        now = datetime.now(timezone.utc)
        order.status = new_status

        if new_status == OrderStatus.COLLECTED:
            order.collected_at = now
        elif new_status == OrderStatus.RESULTED:
            order.resulted_at = now
        elif new_status == OrderStatus.VERIFIED:
            order.verified_at = now
            order.verified_by_id = user_id
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now

        self.db.commit()
        return order

    async def register_specimen(self, data: SpecimenCreate, user_id: str) -> LabSpecimen:
        specimen = LabSpecimen(
            barcode=self._next_barcode(),
            order_id=str(data.order_id),
            specimen_type=data.specimen_type,
            container=data.container,
            volume_ml=data.volume_ml,
            collected_by_id=user_id,
            collected_at=datetime.now(timezone.utc),
            storage_location=data.storage_location,
            notes=data.notes
        )
        self.db.add(specimen)
        self.db.commit()
        self.db.refresh(specimen)

        # Update order status
        order = self.db.query(LabOrder).filter(LabOrder.id == str(data.order_id)).first()
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.COLLECTED
            order.collected_at = datetime.now(timezone.utc)
            self.db.commit()

        return specimen

    async def enter_result(self, data: LabResultCreate, user_id: str) -> LabResult:
        # Auto-flag based on reference ranges
        flag = None
        if data.numeric_value is not None:
            item = self.db.query(LabOrderItem).options(
                joinedload(LabOrderItem.test_panel)
            ).filter(LabOrderItem.id == str(data.order_item_id)).first()

            if item and item.test_panel:
                panel = item.test_panel
                val = data.numeric_value
                # Using female range as default; extend for gender-aware logic
                if panel.critical_high and val >= panel.critical_high:
                    flag = ResultFlag.CRITICAL_HIGH
                elif panel.critical_low and val <= panel.critical_low:
                    flag = ResultFlag.CRITICAL_LOW
                elif panel.normal_range_female_max and val > panel.normal_range_female_max:
                    flag = ResultFlag.HIGH
                elif panel.normal_range_female_min and val < panel.normal_range_female_min:
                    flag = ResultFlag.LOW
                else:
                    flag = ResultFlag.NORMAL

        result = LabResult(
            order_item_id=str(data.order_item_id),
            numeric_value=data.numeric_value,
            text_value=data.text_value,
            unit=data.unit or data.unit,
            flag=flag or data.flag,
            normal_range=data.normal_range,
            method=data.method,
            instrument=data.instrument,
            resulted_by_id=user_id,
            comment=data.comment
        )
        self.db.add(result)

        # Update item status
        item = self.db.query(LabOrderItem).filter(
            LabOrderItem.id == str(data.order_item_id)
        ).first()
        if item:
            item.status = OrderStatus.RESULTED

        self.db.commit()
        self.db.refresh(result)
        return result

    async def verify_result(self, result_id: uuid.UUID, user_id: str):
        result = self.db.query(LabResult).filter(LabResult.id == str(result_id)).first()
        if not result:
            raise ValueError("Result not found")
        result.verified_by_id = user_id
        result.verified_at = datetime.now(timezone.utc)

        # Check if all items in order are verified
        item = self.db.query(LabOrderItem).filter(
            LabOrderItem.id == result.order_item_id
        ).first()
        if item:
            item.status = OrderStatus.VERIFIED
            siblings = self.db.query(LabOrderItem).filter(
                LabOrderItem.order_id == item.order_id
            ).all()
            if all(s.status == OrderStatus.VERIFIED for s in siblings):
                order = self.db.query(LabOrder).filter(LabOrder.id == item.order_id).first()
                if order:
                    order.status = OrderStatus.VERIFIED
                    order.verified_at = datetime.now(timezone.utc)
                    order.verified_by_id = user_id

        self.db.commit()
        return {"status": "verified", "result_id": str(result_id)}

    async def get_patient_results(self, patient_id: uuid.UUID):
        orders = self.db.query(LabOrder).options(
            joinedload(LabOrder.items).joinedload(LabOrderItem.test_panel),
            joinedload(LabOrder.items).joinedload(LabOrderItem.result)
        ).filter(
            LabOrder.patient_id == str(patient_id)
        ).order_by(desc(LabOrder.ordered_at)).all()
        return orders

    # ─── EMBRYOLOGY ─────────────────────────────────────────

    async def create_cycle(self, data: TreatmentCycleCreate) -> TreatmentCycle:
        cycle = TreatmentCycle(
            cycle_number=self._next_cycle_number(),
            patient_id=str(data.patient_id),
            partner_id=str(data.partner_id) if data.partner_id else None,
            cycle_type=data.cycle_type,
            start_date=data.start_date,
            physician_id=str(data.physician_id),
            embryologist_id=str(data.embryologist_id),
            notes=data.notes
        )
        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)
        return cycle

    async def get_cycle(self, cycle_id: uuid.UUID) -> Optional[TreatmentCycle]:
        return self.db.query(TreatmentCycle).options(
            joinedload(TreatmentCycle.oocyte_retrievals),
            joinedload(TreatmentCycle.embryos).joinedload(Embryo.assessments)
        ).filter(TreatmentCycle.id == str(cycle_id)).first()

    async def create_retrieval(self, data: OocyteRetrievalCreate) -> OocyteRetrieval:
        retrieval = OocyteRetrieval(
            patient_id=str(data.patient_id),
            cycle_id=str(data.cycle_id) if data.cycle_id else None,
            visit_id=str(data.visit_id) if data.visit_id else None,
            procedure_date=data.procedure_date,
            physician_id=str(data.physician_id),
            embryologist_id=str(data.embryologist_id),
            anesthesia_type=data.anesthesia_type,
            total_follicles_aspirated=data.total_follicles_aspirated,
            total_oocytes_retrieved=data.total_oocytes_retrieved,
            mii_count=data.mii_count,
            mi_count=data.mi_count,
            gv_count=data.gv_count,
            degenerated_count=data.degenerated_count,
            follicular_fluid_ml=data.follicular_fluid_ml,
            complications=data.complications,
            notes=data.notes
        )
        self.db.add(retrieval)
        self.db.flush()

        # Auto-create individual oocyte records
        if data.total_oocytes_retrieved:
            for i in range(1, data.total_oocytes_retrieved + 1):
                oocyte = Oocyte(
                    retrieval_id=retrieval.id,
                    oocyte_number=i
                )
                self.db.add(oocyte)

        self.db.commit()
        self.db.refresh(retrieval)
        return retrieval

    async def get_retrieval(self, retrieval_id: uuid.UUID) -> Optional[OocyteRetrieval]:
        return self.db.query(OocyteRetrieval).options(
            joinedload(OocyteRetrieval.oocytes).joinedload(Oocyte.fertilization)
        ).filter(OocyteRetrieval.id == str(retrieval_id)).first()

    async def record_fertilization(self, oocyte_id: str, patient_id: str,
                                    status: str, embryologist_id: str,
                                    pronuclei_count: int = None, notes: str = None):
        oocyte = self.db.query(Oocyte).filter(Oocyte.id == oocyte_id).first()
        if not oocyte:
            raise ValueError("Oocyte not found")

        fert = FertilizationRecord(
            oocyte_id=oocyte_id,
            patient_id=patient_id,
            check_time=datetime.now(timezone.utc),
            embryologist_id=embryologist_id,
            status=status,
            pronuclei_count=pronuclei_count,
            notes=notes
        )
        self.db.add(fert)
        self.db.flush()

        # If 2PN → auto-create embryo
        if status == FertilizationStatus.NORMAL_2PN:
            embryo = Embryo(
                embryo_code=self._next_embryo_code(),
                patient_id=patient_id,
                cycle_id=oocyte.retrieval.cycle_id if oocyte.retrieval else None,
                fertilization_record_id=fert.id,
                current_day=1,
                disposition=None
            )
            self.db.add(embryo)

        self.db.commit()
        return fert

    async def add_assessment(self, embryo_id: uuid.UUID, data: EmbryoAssessmentCreate,
                              user_id: str) -> EmbryoAssessment:
        assessment = EmbryoAssessment(
            embryo_id=str(embryo_id),
            assessment_day=data.assessment_day,
            assessment_time=datetime.now(timezone.utc),
            embryologist_id=user_id,
            cell_count=data.cell_count,
            fragmentation_pct=data.fragmentation_pct,
            symmetry=data.symmetry,
            multinucleation=data.multinucleation,
            expansion=data.expansion,
            icm_grade=data.icm_grade,
            te_grade=data.te_grade,
            overall_grade=data.overall_grade,
            is_suitable_transfer=data.is_suitable_transfer,
            is_suitable_freeze=data.is_suitable_freeze,
            notes=data.notes
        )
        self.db.add(assessment)

        # Update embryo current day
        embryo = self.db.query(Embryo).filter(Embryo.id == str(embryo_id)).first()
        if embryo:
            embryo.current_day = data.assessment_day

        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    async def get_assessments(self, embryo_id: uuid.UUID) -> List[EmbryoAssessment]:
        return self.db.query(EmbryoAssessment).filter(
            EmbryoAssessment.embryo_id == str(embryo_id)
        ).order_by(EmbryoAssessment.assessment_day).all()

    async def freeze_embryo(self, embryo_id: uuid.UUID, data: EmbryoCryoCreate,
                             user_id: str):
        cryo = EmbryoCryopreservation(
            embryo_id=str(embryo_id),
            embryologist_id=user_id,
            freeze_date=datetime.now(timezone.utc),
            method=data.method,
            device=data.device,
            device_label=data.device_label,
            tank_id=data.tank_id,
            canister=data.canister,
            goblet=data.goblet,
            position=data.position,
            cryo_medium=data.cryo_medium,
            notes=data.notes
        )
        self.db.add(cryo)

        embryo = self.db.query(Embryo).filter(Embryo.id == str(embryo_id)).first()
        if embryo:
            embryo.disposition = EmbryoDisposition.FROZEN

        self.db.commit()
        return cryo

    async def warm_embryo(self, embryo_id: uuid.UUID, data: EmbryoWarmingCreate,
                           user_id: str):
        warming = EmbryoWarming(
            embryo_id=str(embryo_id),
            embryologist_id=user_id,
            warming_date=data.warming_date,
            status=data.status,
            blastomeres_intact_pct=data.blastomeres_intact_pct,
            post_warm_grade=data.post_warm_grade,
            warming_medium=data.warming_medium,
            notes=data.notes
        )
        self.db.add(warming)

        embryo = self.db.query(Embryo).filter(Embryo.id == str(embryo_id)).first()
        if embryo:
            embryo.disposition = EmbryoDisposition.THAWED

        self.db.commit()
        return warming

    async def record_transfer(self, embryo_id: uuid.UUID, data: EmbryoTransferCreate):
        transfer = EmbryoTransfer(
            embryo_id=str(embryo_id),
            patient_id=str(data.patient_id),
            cycle_id=str(data.cycle_id) if data.cycle_id else None,
            transfer_date=data.transfer_date,
            physician_id=str(data.physician_id),
            embryologist_id=str(data.embryologist_id),
            transfer_type=data.transfer_type,
            endometrial_thickness=data.endometrial_thickness,
            catheter_type=data.catheter_type,
            difficulty=data.difficulty,
            ultrasound_guided=data.ultrasound_guided,
            embryo_position_mm=data.embryo_position_mm,
            notes=data.notes
        )
        self.db.add(transfer)

        embryo = self.db.query(Embryo).filter(Embryo.id == str(embryo_id)).first()
        if embryo:
            embryo.disposition = EmbryoDisposition.FRESH_TRANSFER

        self.db.commit()
        return transfer

    async def get_patient_embryos(self, patient_id: uuid.UUID):
        return self.db.query(Embryo).options(
            joinedload(Embryo.assessments),
            joinedload(Embryo.cryopreservation),
            joinedload(Embryo.warming),
            joinedload(Embryo.transfer)
        ).filter(
            Embryo.patient_id == str(patient_id)
        ).order_by(desc(Embryo.created_at)).all()

    # ─── ANDROLOGY ──────────────────────────────────────────

    async def create_semen_analysis(self, data: SemenAnalysisCreate,
                                     user_id: str) -> SemenAnalysis:
        # Auto-classify per WHO 2021
        diagnosis = self._classify_semen(data)

        analysis = SemenAnalysis(
            analysis_number=self._next_sa_number(),
            patient_id=str(data.patient_id),
            order_id=str(data.order_id) if data.order_id else None,
            collected_at=data.collected_at,
            abstinence_days=data.abstinence_days,
            collection_method=data.collection_method,
            collection_location=data.collection_location,
            analyst_id=user_id,
            volume_ml=data.volume_ml,
            appearance=data.appearance,
            color=data.color,
            viscosity=data.viscosity,
            liquefaction_time_min=data.liquefaction_time_min,
            ph=data.ph,
            concentration_M_per_ml=data.concentration_M_per_ml,
            total_count_M=data.total_count_M,
            total_motility_pct=data.total_motility_pct,
            progressive_motility_pct=data.progressive_motility_pct,
            non_progressive_pct=data.non_progressive_pct,
            immotile_pct=data.immotile_pct,
            normal_morphology_pct=data.normal_morphology_pct,
            vitality_pct=data.vitality_pct,
            vitality_method=data.vitality_method,
            wbc_per_ml=data.wbc_per_ml,
            agglutination=data.agglutination,
            dfi_pct=data.dfi_pct,
            dfi_method=data.dfi_method,
            diagnosis=diagnosis or data.diagnosis,
            recommendation=data.recommendation,
            notes=data.notes
        )

        # Check if WHO reference met
        analysis.who_reference_met = self._check_who_reference(data)

        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def _classify_semen(self, data: SemenAnalysisCreate) -> Optional[str]:
        """WHO 2021 classification"""
        issues = []

        if data.volume_ml is not None and data.volume_ml < Decimal("1.4"):
            issues.append("hypospermia")
        if data.concentration_M_per_ml is not None and data.concentration_M_per_ml < Decimal("16"):
            issues.append("oligozoospermia")
        if data.concentration_M_per_ml is not None and data.concentration_M_per_ml == 0:
            return "azoospermia"
        if data.total_motility_pct is not None and data.total_motility_pct < Decimal("42"):
            issues.append("asthenozoospermia")
        if data.normal_morphology_pct is not None and data.normal_morphology_pct < Decimal("4"):
            issues.append("teratozoospermia")

        if not issues:
            return "normozoospermia"
        if len(issues) == 3 and "oligozoospermia" in issues:
            return "oligoasthenoteratozoospermia"
        return "+".join(issues)

    def _check_who_reference(self, data: SemenAnalysisCreate) -> bool:
        """Check against WHO 2021 5th percentile reference values"""
        checks = []
        if data.volume_ml is not None:
            checks.append(data.volume_ml >= Decimal("1.4"))
        if data.concentration_M_per_ml is not None:
            checks.append(data.concentration_M_per_ml >= Decimal("16"))
        if data.total_motility_pct is not None:
            checks.append(data.total_motility_pct >= Decimal("42"))
        if data.progressive_motility_pct is not None:
            checks.append(data.progressive_motility_pct >= Decimal("30"))
        if data.normal_morphology_pct is not None:
            checks.append(data.normal_morphology_pct >= Decimal("4"))
        if data.vitality_pct is not None:
            checks.append(data.vitality_pct >= Decimal("54"))
        return all(checks) if checks else True

    async def get_semen_analyses(self, patient_id: uuid.UUID) -> List[SemenAnalysis]:
        return self.db.query(SemenAnalysis).filter(
            SemenAnalysis.patient_id == str(patient_id)
        ).order_by(desc(SemenAnalysis.created_at)).all()

    async def create_sperm_prep(self, data: dict, user_id: str) -> SpermPreparation:
        prep = SpermPreparation(
            semen_analysis_id=data.get("semen_analysis_id"),
            cycle_id=data.get("cycle_id"),
            patient_id=data["patient_id"],
            preparation_method=data.get("preparation_method"),
            prepared_at=datetime.now(timezone.utc),
            embryologist_id=user_id,
            post_volume_ml=data.get("post_volume_ml"),
            post_concentration_M_ml=data.get("post_concentration_M_ml"),
            post_motility_pct=data.get("post_motility_pct"),
            post_progressive_pct=data.get("post_progressive_pct"),
            post_total_motile_M=data.get("post_total_motile_M"),
            recovery_rate_pct=data.get("recovery_rate_pct"),
            used_for=data.get("used_for"),
            notes=data.get("notes")
        )
        self.db.add(prep)
        self.db.commit()
        self.db.refresh(prep)
        return prep
