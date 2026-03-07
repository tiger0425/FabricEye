from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import random
import urllib.parse

from app.core.database import get_db
from app.models.roll import Roll, RollStatus
from app.models.defect import Defect, DefectType, DefectTypeCN, DefectSeverity
from app.schemas.roll import RollCreate, RollUpdate, RollResponse
from app.utils.response import success, error
from app.services.cascade import CascadeEngine
from app.services.four_point_scoring import FourPointScorer, DEFAULT_WIDTH_CM

router = APIRouter(
    prefix="/rolls",
    tags=["Rolls"],
    responses={404: {"description": "Not found"}},
)

# 全局存储正在运行的引擎实例
active_engines: Dict[int, CascadeEngine] = {}

@router.post("/")
async def create_roll(roll: RollCreate, db: AsyncSession = Depends(get_db)):
    db_roll = Roll(
        roll_number=roll.roll_number,
        fabric_type=roll.fabric_type,
        batch_number=roll.batch_number,
        length_meters=roll.length_meters,
        width_cm=roll.width_cm,
        status=RollStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_roll)
    try:
        await db.commit()
        await db.refresh(db_roll)
    except Exception as e:
        await db.rollback()
        return error(f"创建失败: {str(e)}")
    return success(RollResponse.model_validate(db_roll))

@router.get("/")
async def list_rolls(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    status: Optional[RollStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * pageSize
    query = select(Roll).offset(skip).limit(pageSize).order_by(Roll.created_at.desc())
    if status:
        query = query.where(Roll.status == status)
    result = await db.execute(query)
    rolls = result.scalars().all()
    count_stmt = select(func.count()).select_from(Roll)
    if status:
        count_stmt = count_stmt.where(Roll.status == status)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()
    # 手动填充 videoId
    roll_list = []
    from app.models.video import Video
    for r in rolls:
        video_result = await db.execute(
            select(Video.id).where(Video.roll_id == r.id).order_by(Video.id.desc()).limit(1)
        )
        latest_video_id = video_result.scalar()
        
        # 转换为响应模型并手动注入字段
        res_data = RollResponse.model_validate(r)
        # 注意：这里我们构造一个字典来强制使用 CamelCase 别名
        data_dict = res_data.model_dump(by_alias=True)
        data_dict["videoId"] = latest_video_id
        
        roll_list.append(data_dict)

    return success({
        "list": roll_list,
        "total": total
    })
    return success({
        "list": roll_list,
        "total": total
    })

@router.get("/{roll_id}")
async def get_roll(roll_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    roll = result.scalar_one_or_none()
    if roll is None:
        return error("布卷不存在", code=404)
    return success(RollResponse.model_validate(roll))

@router.put("/{roll_id}")
async def update_roll(roll_id: int, roll_update: RollUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)
    update_data = roll_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_roll, key, value)
    db_roll.updated_at = datetime.utcnow()
    try:
        await db.commit()
        await db.refresh(db_roll)
    except Exception as e:
        await db.rollback()
        return error(f"更新失败: {str(e)}")
    return success(RollResponse.model_validate(db_roll))

@router.delete("/{roll_id}")
async def delete_roll(roll_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)
    if roll_id in active_engines:
        active_engines[roll_id].stop()
        del active_engines[roll_id]
    await db.delete(db_roll)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        return error(f"删除失败: {str(e)}")
    return success(message="删除成功")

@router.post("/{roll_id}/start")
async def start_roll_inspection(roll_id: int, db: AsyncSession = Depends(get_db)):
    """开始验布 - 真实引擎模式"""
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)
    
    # 检查是否已在验布中
    if roll_id in active_engines:
        return error(f"该布卷已在验布中")
    
    try:
        # 初始化并启动级联检测引擎
        engine = CascadeEngine(roll_id)
        if not await engine.start():
            return error("启动失败: 无法打开摄像头或初始化模型")
            
        active_engines[roll_id] = engine
        
        # 更新布卷状态
        db_roll.status = RollStatus.INSPECTING
        db_roll.updated_at = datetime.utcnow()
        await db.commit()
        
        return success(message="已开始验布")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error(f"启动失败: {str(e)}")

@router.post("/{roll_id}/stop")
async def stop_roll_inspection(roll_id: int, db: AsyncSession = Depends(get_db)):
    """停止验布"""
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    db_roll = result.scalar_one_or_none()
    if db_roll is None:
        return error("布卷不存在", code=404)
    
    # 从活跃引擎中移除并停止
    if roll_id in active_engines:
        engine = active_engines[roll_id]
        engine.stop()
        del active_engines[roll_id]
    
    # 更新布卷状态
    db_roll.status = RollStatus.COMPLETED
    db_roll.updated_at = datetime.utcnow()
    await db.commit()
    
    return success(message="已停止验布")

@router.get("/{roll_id}/cascade-status")
async def get_cascade_status(roll_id: int):
    """获取级联状态"""
    if roll_id not in active_engines:
        return success({
            "is_running": False,
            "roll_id": roll_id,
            "status": "stopped"
        })
    
    engine = active_engines[roll_id]
    return success(engine.get_status())

@router.get("/{roll_id}/report")
async def get_roll_report(roll_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    roll = result.scalar_one_or_none()
    if roll is None:
        return error("布卷不存在", code=404)
    defects_result = await db.execute(
        select(Defect)
        .where(Defect.roll_id == roll_id)
        .order_by(Defect.detected_at.desc())
    )
    defects = defects_result.scalars().all()
    severe_count = sum(1 for d in defects if d.severity == DefectSeverity.SEVERE)
    moderate_count = sum(1 for d in defects if d.severity == DefectSeverity.MODERATE)
    minor_count = sum(1 for d in defects if d.severity == DefectSeverity.MINOR)
    type_counts: Dict[DefectType, int] = {}
    for d in defects:
        if d.defect_type is not None:
            type_counts[d.defect_type] = type_counts.get(d.defect_type, 0) + 1
    total_defects = len(defects)
    by_type = []
    for dt, count in type_counts.items():
        percentage = round((count / total_defects * 100), 2) if total_defects > 0 else 0.0
        by_type.append({
            "type": dt.value,
            "type_cn": DefectTypeCN.get_cn(dt),
            "count": count,
            "percentage": percentage,
        })
    quality_score = max(0, 100 - (severe_count * 10) - (moderate_count * 5) - (minor_count * 2))

    # ====== 四分制评分 ======
    scorer = FourPointScorer()
    roll_length = roll.length_meters or 100.0  # 缺省100米
    roll_width = roll.width_cm or DEFAULT_WIDTH_CM
    four_point_result = scorer.calculate_roll_score(defects, roll_length, roll_width)

    def _serialize_defect(d: Defect) -> dict:
        # 从四分制结果中查找该缺陷的评分
        ds = next((s for s in four_point_result.per_defect_scores if s.defect_id == d.id), None)
        return {
            "id": d.id,
            "roll_id": d.roll_id,
            "defect_type": d.defect_type.value if d.defect_type else None,
            "defect_type_cn": d.defect_type_cn,
            "confidence": d.confidence,
            "severity": d.severity.value if d.severity else None,
            "position_meter": d.position_meter,
            "timestamp": d.timestamp,
            "bbox_x1": d.bbox_x1,
            "bbox_y1": d.bbox_y1,
            "bbox_x2": d.bbox_x2,
            "bbox_y2": d.bbox_y2,
            "defect_length_cm": d.defect_length_cm,
            "point_score": ds.point_score if ds else (d.point_score),
            "snapshot_path": d.snapshot_path,
            "detected_at": d.detected_at.isoformat() if d.detected_at else None,
            "reviewed": d.reviewed,
            "reviewed_result": d.reviewed_result.value if d.reviewed_result else None,
        }
    report = {
        "roll": {
            "id": roll.id,
            "roll_number": roll.roll_number,
            "fabric_type": roll.fabric_type,
            "batch_number": roll.batch_number,
            "length_meters": roll.length_meters,
            "width_cm": roll.width_cm,
            "status": roll.status.value if roll.status else None,
            "created_at": roll.created_at.isoformat() if roll.created_at else None,
        },
        "summary": {
            "total_defects": total_defects,
            "by_severity": {
                "severe": severe_count,
                "moderate": moderate_count,
                "minor": minor_count,
            },
            "by_type": by_type,
            "quality_score": quality_score,
            "four_point": {
                "total_points": four_point_result.total_points,
                "points_per_100sqyd": four_point_result.points_per_100sqyd,
                "grade": four_point_result.grade,
                "pass_threshold": four_point_result.pass_threshold,
                "is_pass": four_point_result.is_pass,
                "score_distribution": four_point_result.score_distribution,
            },
        },
        "defects": [_serialize_defect(d) for d in defects],
        "generated_at": datetime.utcnow().isoformat(),
    }
    return success(report)


@router.get("/{roll_id}/report/pdf")
async def download_roll_report_pdf(roll_id: int, db: AsyncSession = Depends(get_db)):
    """生成并下载验布报告 PDF"""
    # 1. 获取布卷信息
    result = await db.execute(select(Roll).where(Roll.id == roll_id))
    roll = result.scalar_one_or_none()
    if not roll:
        raise HTTPException(status_code=404, detail="布卷不存在")

    # 2. 获取缺陷列表
    defect_result = await db.execute(
        select(Defect).where(Defect.roll_id == roll_id).order_by(Defect.detected_at)
    )
    defects = defect_result.scalars().all()

    # 3. 计算四分制评分（使用正确的 API）
    scorer = FourPointScorer()
    four_point = scorer.calculate_roll_score(
        defects=defects,
        roll_length_m=roll.length_meters or 100.0,
        roll_width_cm=roll.width_cm or DEFAULT_WIDTH_CM,
    )

    # 4. 构建缺陷行 HTML
    defect_rows_html = ""
    severity_map = {"severe": "严重", "moderate": "中等", "minor": "轻微"}
    type_map = {
        "hole": "破洞", "stain": "污渍", "snag": "拉丝",
        "weaving_error": "织纵缺陷", "skip": "跳证", "other": "其他"
    }
    point_colors = {1: "#64748b", 2: "#f59e0b", 3: "#ef4444", 4: "#b91c1c"}
    for i, d in enumerate(defects, 1):
        sev = d.severity.value if d.severity else "minor"
        sev_cn = severity_map.get(sev, sev)
        typ = d.defect_type.value if d.defect_type else "other"
        typ_cn = type_map.get(typ, typ)
        pos_m = getattr(d, 'position_meter', None)
        pos_str = f"{pos_m:.2f} m" if pos_m is not None else "-"
        ps = d.point_score or 1
        pc = point_colors.get(ps, "#64748b")
        length_str = f"{d.defect_length_cm:.1f} cm" if d.defect_length_cm else "-"
        defect_rows_html += f"""
        <tr>
          <td>{i}</td>
          <td>{typ_cn}</td>
          <td style="color:{'#ef4444' if sev=='severe' else '#f59e0b' if sev=='moderate' else '#6b7280'}; font-weight:600">{sev_cn}</td>
          <td>{length_str}</td>
          <td style="color:{pc}; font-weight:700; text-align:center">{ps}分</td>
          <td>{pos_str}</td>
        </tr>"""

    # 四分制颜色标识
    fp_color = "#22c55e" if four_point.is_pass else "#ef4444"
    fp_label = "合格" if four_point.is_pass else "不合格"
    dist = four_point.score_distribution or {}

    # 5. 完整 HTML 模板
    report_date = datetime.utcnow().strftime("%Y/%m/%d %H:%M")
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<style>
  body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background:#fff; color:#1a202c; margin:0; padding:32px; }}
  .header {{ background: linear-gradient(135deg,#1e3a5f,#2563eb); color:#fff; padding:28px 32px;
             border-radius:8px 8px 0 0; display:flex; justify-content:space-between; align-items:start; }}
  .brand {{ font-size:26px; font-weight:800; letter-spacing:2px; }}
  .brand span {{ color:#93c5fd; }}
  .brand-sub {{ font-size:12px; opacity:.7; margin-top:4px; }}
  .meta {{ text-align:right; font-size:12px; opacity:.85; line-height:1.8; }}
  .body {{ padding:28px 32px; }}
  .section {{ margin-bottom:28px; }}
  .section-title {{ font-size:15px; font-weight:700; color:#1e3a5f; padding-bottom:8px; border-bottom:2px solid #2563eb; margin-bottom:14px; }}
  .info-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
  .info-item {{ background:#f0f4ff; border-radius:6px; padding:12px 14px; }}
  .info-label {{ font-size:11px; color:#64748b; margin-bottom:3px; }}
  .info-value {{ font-size:14px; font-weight:600; color:#1e3a5f; }}
  .fp-box {{ display:flex; align-items:center; gap:24px; background:#fdf6ec; border:1px solid #faecd8; border-radius:10px; padding:20px 24px; }}
  .fp-ring {{ width:80px; height:80px; border-radius:50%; border:5px solid {fp_color}; display:flex; align-items:center; justify-content:center; flex-shrink:0; }}
  .fp-score {{ font-size:22px; font-weight:800; color:{fp_color}; }}
  .stats-row {{ display:flex; gap:14px; }}
  .stat {{ flex:1; border-radius:8px; padding:16px; text-align:center; color:#fff; }}
  .stat-num {{ font-size:28px; font-weight:800; }}
  .stat-lbl {{ font-size:12px; opacity:.85; margin-top:4px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#1e3a5f; color:#fff; padding:10px 12px; text-align:left; font-weight:600; }}
  td {{ padding:9px 12px; border-bottom:1px solid #e2e8f0; }}
  tr:nth-child(even) td {{ background:#f8fafc; }}
  .footer {{ background:#f0f4ff; padding:16px 32px; display:flex; justify-content:space-between;
             font-size:11px; color:#94a3b8; border-top:1px solid #e2e8f0; border-radius:0 0 8px 8px; }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">Fabric<span>Eye</span></div>
      <div class="brand-sub">AI 智能验布系统</div>
    </div>
    <div class="meta">
      <div>布卷号：{roll.roll_number or '-'}</div>
      <div>批次：{roll.batch_number or '-'}</div>
      <div>日期：{report_date}</div>
    </div>
  </div>

  <div class="body">
    <div class="section">
      <div class="section-title">布卷信息</div>
      <div class="info-grid">
        <div class="info-item"><div class="info-label">布卷号</div><div class="info-value">{roll.roll_number or '-'}</div></div>
        <div class="info-item"><div class="info-label">面料类型</div><div class="info-value">{roll.fabric_type or '-'}</div></div>
        <div class="info-item"><div class="info-label">批次号</div><div class="info-value">{roll.batch_number or '-'}</div></div>
        <div class="info-item"><div class="info-label">长度(米)</div><div class="info-value">{roll.length_meters or '-'}</div></div>
        <div class="info-item"><div class="info-label">布幅(厘米)</div><div class="info-value">{roll.width_cm or '-'}</div></div>
        <div class="info-item"><div class="info-label">报告日期</div><div class="info-value">{report_date}</div></div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">四分制评分 (ASTM D5430)</div>
      <div class="fp-box">
        <div class="fp-ring"><div class="fp-score">{four_point.points_per_100sqyd}</div></div>
        <div>
          <div style="font-size:15px;font-weight:700;color:#1e3a5f;">{four_point.grade}</div>
          <div style="color:{fp_color};font-weight:700;font-size:14px;margin-top:4px;">{fp_label} &nbsp; (及格线: {four_point.pass_threshold})</div>
          <div style="font-size:13px;color:#475569;margin-top:6px;">
            总罚分: <strong>{four_point.total_points}</strong> | 
            1分: {dist.get('1分',0)} &nbsp; 2分: {dist.get('2分',0)} &nbsp; 3分: {dist.get('3分',0)} &nbsp; 4分: {dist.get('4分',0)}
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">缺陷统计</div>
      <div class="stats-row">
        <div class="stat" style="background:#2563eb"><div class="stat-num">{len(defects)}</div><div class="stat-lbl">总缺陷</div></div>
        <div class="stat" style="background:#ef4444"><div class="stat-num">{sum(1 for d in defects if d.severity and d.severity.value=='severe')}</div><div class="stat-lbl">严重</div></div>
        <div class="stat" style="background:#f59e0b"><div class="stat-num">{sum(1 for d in defects if d.severity and d.severity.value=='moderate')}</div><div class="stat-lbl">中等</div></div>
        <div class="stat" style="background:#6b7280"><div class="stat-num">{sum(1 for d in defects if d.severity and d.severity.value=='minor')}</div><div class="stat-lbl">轻微</div></div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">缺陷详情列表</div>
      {'<table><thead><tr><th>#</th><th>类型</th><th>严重程度</th><th>长度</th><th>评分</th><th>位置(距卷首)</th></tr></thead><tbody>' + defect_rows_html + '</tbody></table>' if defects else '<p style="color:#94a3b8;text-align:center;padding:20px 0;">未检测到缺陷</p>'}
    </div>
  </div>

  <div class="footer">
    <span>FabricEye AI 验布系统 &middot; 自动生成报告</span>
    <span>生成时间：{report_date}</span>
  </div>
</body>
</html>"""

    # 6. 使用 fpdf2 生成 PDF（纯 Python，Windows 无需额外系统依赖）
    try:
        from fpdf import FPDF
        import os

        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # 尝试加载 Windows 中文字体
        font_paths = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
        ]
        font_loaded = False
        for fp in font_paths:
            if os.path.exists(fp):
                pdf.add_font("zh", "", fp, uni=True)
                font_loaded = True
                break
        zh = "zh" if font_loaded else "Helvetica"

        # ---- 标题背景 ----
        pdf.set_fill_color(30, 58, 95)
        pdf.rect(0, 0, 210, 36, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(zh, size=18)
        pdf.set_xy(15, 7)
        pdf.cell(0, 10, "FabricEye  AI 验布报告", ln=True)
        pdf.set_font(zh, size=9)
        pdf.set_xy(15, 20)
        pdf.cell(0, 8, f"布卷号: {roll.roll_number or '-'}   批次: {roll.batch_number or '-'}   日期: {report_date}", ln=True)

        # ---- 辅助函数 ----
        def section_title(text):
            pdf.set_fill_color(30, 58, 95)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font(zh, size=11)
            pdf.cell(0, 8, text, ln=True, fill=True)
            pdf.set_text_color(26, 32, 44)
            pdf.ln(2)

        def kv_row(label, value):
            pdf.set_font(zh, size=9)
            pdf.set_x(15)
            pdf.set_fill_color(240, 244, 255)
            pdf.cell(50, 7, label, border=0, fill=True)
            pdf.set_fill_color(255, 255, 255)
            pdf.cell(0, 7, str(value), border=0, ln=True)

        pdf.set_text_color(26, 32, 44)
        pdf.set_y(42)

        # -- 布卷信息 --
        section_title("  布卷信息")
        kv_row("布卷号:", roll.roll_number or '-')
        kv_row("面料类型:", roll.fabric_type or '-')
        kv_row("批次号:", roll.batch_number or '-')
        kv_row("长度 (m):", str(roll.length_meters or '-'))
        kv_row("布幅 (cm):", str(roll.width_cm or '-'))
        pdf.ln(4)

        # -- 四分制评分 --
        section_title("  四分制评分 (ASTM D5430)")
        fp_pass_str = "合格" if four_point.is_pass else "不合格"
        kv_row("综合评级:", four_point.grade)
        kv_row("分/百码²:", str(four_point.points_per_100sqyd))
        kv_row("及格线:", str(four_point.pass_threshold))
        kv_row("结论:", fp_pass_str)
        kv_row("总罚分:", str(four_point.total_points))
        dist_str = f"1分:{dist.get('1分',0)}  2分:{dist.get('2分',0)}  3分:{dist.get('3分',0)}  4分:{dist.get('4分',0)}"
        kv_row("分布:", dist_str)
        pdf.ln(4)

        # -- 缺陷统计 --
        section_title("  缺陷统计")
        severe_n = sum(1 for d in defects if d.severity and d.severity.value == 'severe')
        moderate_n = sum(1 for d in defects if d.severity and d.severity.value == 'moderate')
        minor_n = sum(1 for d in defects if d.severity and d.severity.value == 'minor')
        kv_row("总缺陷数:", str(len(defects)))
        kv_row("严重:", str(severe_n))
        kv_row("中等:", str(moderate_n))
        kv_row("轻微:", str(minor_n))
        pdf.ln(4)

        # -- 缺陷详情表格 --
        if defects:
            section_title("  缺陷详情列表")
            pdf.set_font(zh, size=8)
            pdf.set_fill_color(30, 58, 95)
            pdf.set_text_color(255, 255, 255)
            pdf.set_x(15)
            headers = ["#", "类型", "严重程度", "长度", "评分", "位置(距卷首)"]
            widths  = [10,  28,    22,       24,   18,   68]
            for h, w in zip(headers, widths):
                pdf.cell(w, 7, h, border=0, fill=True)
            pdf.ln()
            pdf.set_text_color(26, 32, 44)

            sev_map = {"severe": "严重", "moderate": "中等", "minor": "轻微"}
            typ_map = {"hole": "破洞", "stain": "污渍", "snag": "拉丝",
                       "weaving_error": "织纵缺陷", "skip": "跳纱", "other": "其他",
                       "color_variance": "色差", "weft_break": "断纬", "warp_break": "断经"}

            for i, d in enumerate(defects, 1):
                fill_color = (248, 250, 252) if i % 2 == 0 else (255, 255, 255)
                pdf.set_fill_color(*fill_color)
                sev = d.severity.value if d.severity else "minor"
                typ = d.defect_type.value if d.defect_type else "other"
                pos_m = getattr(d, 'position_meter', None)
                pos_str = f"{pos_m:.2f} m" if pos_m is not None else "-"
                length_str = f"{d.defect_length_cm:.1f} cm" if d.defect_length_cm else "-"
                row_vals = [
                    str(i),
                    typ_map.get(typ, typ),
                    sev_map.get(sev, sev),
                    length_str,
                    f"{d.point_score or 1} 分",
                    pos_str,
                ]
                pdf.set_x(15)
                for val, w in zip(row_vals, widths):
                    pdf.cell(w, 6, val, border=0, fill=True)
                pdf.ln()

        # ---- 缺陷地图（Defect Map）----
        # 绘制纵向布卷长度轴，标注缺陷位置
        defects_with_pos = [d for d in defects if getattr(d, 'position_meter', None) is not None]
        if defects_with_pos:
            pdf.add_page()
            section_title("  缺陷地图 (Defect Map)")

            total_len = roll.length_meters or 100.0
            # 地图区域：左边留 35mm 放文字，右边留 15mm，轴高 200mm
            axis_x = 50      # 轴线 X 坐标（mm）
            axis_y_top = pdf.get_y() + 5
            axis_y_bot = axis_y_top + 180
            axis_h = axis_y_bot - axis_y_top
            label_x = 15    # 标签文字起始 X

            # 绘制轴线
            pdf.set_draw_color(100, 116, 139)
            pdf.set_line_width(0.8)
            pdf.line(axis_x, axis_y_top, axis_x, axis_y_bot)

            # 刻度（每 5m 一条）
            step_m = 5.0
            tick_count = int(total_len / step_m) + 1
            pdf.set_font(zh, size=7)
            pdf.set_text_color(100, 116, 139)
            for i in range(tick_count):
                meter = i * step_m
                if meter > total_len:
                    break
                y = axis_y_top + (meter / total_len) * axis_h
                pdf.line(axis_x - 3, y, axis_x, y)
                pdf.set_xy(label_x, y - 3)
                pdf.cell(axis_x - label_x - 1, 6, f"{meter:.0f}m", align='R')

            # 画末尾刻度
            pdf.line(axis_x - 3, axis_y_bot, axis_x, axis_y_bot)
            pdf.set_xy(label_x, axis_y_bot - 3)
            pdf.cell(axis_x - label_x - 1, 6, f"{total_len:.0f}m", align='R')

            # 标注每个缺陷
            sev_colors = {
                "severe": (239, 68, 68),    # 红色
                "moderate": (245, 158, 11),  # 橙色
                "minor": (107, 114, 128),    # 灰色
            }
            typ_map_short = {"hole": "破洞", "stain": "污渍", "snag": "拉丝",
                             "weaving_error": "断纬", "warp_break": "断经",
                             "weft_break": "断纬", "color_variance": "色差", "other": "其他"}

            for i, d in enumerate(defects_with_pos):
                pos_m = d.position_meter
                y = axis_y_top + (pos_m / total_len) * axis_h
                sev = d.severity.value if d.severity else "minor"
                typ = d.defect_type.value if d.defect_type else "other"
                color = sev_colors.get(sev, (107, 114, 128))

                # 画小圆点
                pdf.set_fill_color(*color)
                pdf.ellipse(axis_x + 1, y - 2.5, 5, 5, 'F')

                # 标签
                ps = d.point_score or 1
                label_text = f"{typ_map_short.get(typ, typ)}  {pos_m:.1f}m  [{ps}分]"
                pdf.set_font(zh, size=7.5)
                pdf.set_text_color(*color)
                pdf.set_xy(axis_x + 8, y - 3.5)
                pdf.cell(130, 7, label_text)

            # 图例
            pdf.set_text_color(26, 32, 44)
            pdf.set_xy(axis_x + 8, axis_y_bot + 8)
            pdf.set_font(zh, size=8)
            for sev_key, sev_label, color in [
                ("severe", "严重缺陷", (239, 68, 68)),
                ("moderate", "中等缺陷", (245, 158, 11)),
                ("minor", "轻微缺陷", (107, 114, 128)),
            ]:
                pdf.set_fill_color(*color)
                pdf.circle(pdf.get_x() + 2, pdf.get_y() + 3.5, 2.5, 'F')
                pdf.set_x(pdf.get_x() + 7)
                pdf.cell(28, 7, sev_label)
            pdf.ln(10)

        # ---- 严重缺陷证据照片 ----
        from PIL import Image as PILImage
        severe_with_snap = [
            d for d in defects
            if d.severity and d.severity.value == 'severe'
            and getattr(d, 'snapshot_path', None)
            and os.path.exists(d.snapshot_path)
        ]
        if severe_with_snap:
            pdf.add_page()
            section_title("  严重缺陷证据照片")
            pdf.set_font(zh, size=8.5)
            pdf.set_text_color(71, 85, 105)
            pdf.cell(0, 6, "以下照片由 FabricEye 工业相机自动捕获，可作为质量纠纷凭证。", ln=True)
            pdf.ln(3)

            sev_map2 = {"severe": "严重", "moderate": "中等", "minor": "轻微"}
            typ_map2 = {"hole": "破洞", "stain": "污渍", "snag": "拉丝",
                        "weaving_error": "织纵缺陷", "warp_break": "断经",
                        "weft_break": "断纬", "color_variance": "色差", "other": "其他"}

            # 每行两张，图片宽 85mm
            IMG_W = 85
            IMG_H = 65
            COL_GAP = 10
            col = 0
            start_y = pdf.get_y()
            row_y = start_y

            for idx, d in enumerate(severe_with_snap):
                sev = d.severity.value if d.severity else "severe"
                typ = d.defect_type.value if d.defect_type else "other"
                pos_m = getattr(d, 'position_meter', None)
                pos_str = f"{pos_m:.2f} m" if pos_m is not None else "未知位置"
                length_str = f"{d.defect_length_cm:.1f} cm" if d.defect_length_cm else "-"
                ps = d.point_score or 4

                img_x = 15 + col * (IMG_W + COL_GAP)
                img_y = row_y

                # 标题
                pdf.set_font(zh, size=8)
                pdf.set_text_color(239, 68, 68)
                pdf.set_xy(img_x, img_y)
                pdf.cell(IMG_W, 6, f"[{idx+1}] {typ_map2.get(typ, typ)} · {pos_str} · {length_str} · {ps}分", ln=False)

                # 插入图片
                try:
                    pdf.image(d.snapshot_path, x=img_x, y=img_y + 7, w=IMG_W, h=IMG_H)
                except Exception:
                    pass  # 图片加载失败时跳过

                # 边框
                pdf.set_draw_color(239, 68, 68)
                pdf.set_line_width(0.5)
                pdf.rect(img_x, img_y + 7, IMG_W, IMG_H)

                col += 1
                if col >= 2:
                    col = 0
                    row_y = img_y + IMG_H + 16  # 下一行
                    pdf.set_y(row_y)

        # ---- 页脚 ----
        pdf.set_auto_page_break(auto=False)
        pdf.set_y(-20)
        pdf.set_fill_color(240, 244, 255)
        pdf.rect(0, pdf.get_y(), 210, 20, 'F')
        pdf.set_text_color(148, 163, 184)
        pdf.set_font(zh, size=8)
        pdf.set_x(15)
        pdf.cell(100, 8, "FabricEye AI 验布系统  自动生成报告")
        pdf.cell(0, 8, f"生成时间: {report_date}", align='R')

        pdf_bytes = bytes(pdf.output())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF生成失败: {str(e)}")

    # 7. 返回带正确文件名的 HTTP 响应 - 浏览器必定尊重
    safe_name = f"验布报告-{roll.roll_number or 'report'}-{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    encoded_name = urllib.parse.quote(safe_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            "Content-Length": str(len(pdf_bytes)),
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
    )
