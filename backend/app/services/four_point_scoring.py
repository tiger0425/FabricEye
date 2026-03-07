"""
FabricEye AI验布系统 - 四分制评分服务（ASTM D5430）

美标四分制是全球纺织品验布的事实标准：
- ≤ 3 英寸 (7.5cm) → 1 分
- 3-6 英寸 (7.5-15cm) → 2 分
- 6-9 英寸 (15-23cm) → 3 分
- > 9 英寸 (23cm) 或破洞 → 4 分

核心公式：
  每百平方码罚分 = (总罚分 × 100 × 36) / (检验长度码 × 布幅英寸)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


# 缺陷长度 → 罚分 的阈值（单位：厘米）
_THRESHOLDS_CM = [
    (7.5, 1),   # ≤ 7.5cm → 1 分
    (15.0, 2),  # 7.5-15cm → 2 分
    (23.0, 3),  # 15-23cm → 3 分
]
_MAX_SCORE = 4  # > 23cm 或破洞

# 破洞类型无论尺寸都给 4 分
_HOLE_TYPES = {"hole"}

# 单位换算常量
_CM_PER_INCH = 2.54
_CM_PER_YARD = 91.44  # 1 码 = 91.44 厘米
_INCH_PER_CM = 1 / _CM_PER_INCH

# 默认布幅（厘米），当用户未填写时使用
DEFAULT_WIDTH_CM = 150.0

# 默认及格阈值（每百平方码罚分）
DEFAULT_PASS_THRESHOLD = 40


@dataclass
class DefectScore:
    """单个缺陷的四分制评分"""
    defect_id: Optional[int] = None
    defect_type: str = ""
    defect_length_cm: float = 0.0
    point_score: int = 0
    reason: str = ""


@dataclass
class FourPointResult:
    """布卷四分制评分结果"""
    total_points: int = 0
    points_per_100sqyd: float = 0.0
    grade: str = "未评定"
    is_pass: bool = False
    pass_threshold: float = DEFAULT_PASS_THRESHOLD
    score_distribution: Dict[str, int] = field(default_factory=lambda: {
        "1分": 0, "2分": 0, "3分": 0, "4分": 0
    })
    per_defect_scores: List[DefectScore] = field(default_factory=list)
    roll_length_m: float = 0.0
    roll_width_cm: float = DEFAULT_WIDTH_CM
    total_defects: int = 0


class FourPointScorer:
    """
    四分制评分引擎

    使用方法:
        scorer = FourPointScorer()
        score = scorer.score_defect("stain", 5.0)       # 返回 1
        result = scorer.calculate_roll_score(defects, 100.0, 150.0)
    """

    def __init__(self, pass_threshold: float = DEFAULT_PASS_THRESHOLD):
        self.pass_threshold = pass_threshold

    def score_defect(self, defect_type: str, defect_length_cm: float) -> int:
        """
        对单个缺陷评分

        Args:
            defect_type: 缺陷类型（如 "hole", "stain" 等）
            defect_length_cm: 缺陷长度（厘米）

        Returns:
            四分制评分 (1-4)
        """
        # 破洞无论尺寸都给 4 分
        if defect_type.lower() in _HOLE_TYPES:
            return _MAX_SCORE

        # 根据长度区间评分
        if defect_length_cm <= 0:
            return 1  # 无长度信息视为最小评分

        for threshold_cm, score in _THRESHOLDS_CM:
            if defect_length_cm <= threshold_cm:
                return score

        return _MAX_SCORE

    def calculate_roll_score(
        self,
        defects: list,
        roll_length_m: float,
        roll_width_cm: float = DEFAULT_WIDTH_CM,
    ) -> FourPointResult:
        """
        计算整卷布的四分制评分

        Args:
            defects: 缺陷列表，每项需有 defect_type、defect_length_cm 属性或键
            roll_length_m: 布卷长度（米）
            roll_width_cm: 布幅宽度（厘米）

        Returns:
            FourPointResult 评分结果
        """
        result = FourPointResult(
            pass_threshold=self.pass_threshold,
            roll_length_m=roll_length_m,
            roll_width_cm=roll_width_cm,
        )

        if not defects:
            result.grade = self.determine_grade(0)
            result.is_pass = True
            return result

        total_points = 0
        distribution = {"1分": 0, "2分": 0, "3分": 0, "4分": 0}
        per_defect_scores = []

        for d in defects:
            # 支持字典和对象两种数据格式
            if isinstance(d, dict):
                defect_type = d.get("defect_type", "unknown")
                defect_length_cm = d.get("defect_length_cm") or 0.0
                defect_id = d.get("id")
            else:
                defect_type = getattr(d, "defect_type", "unknown")
                # 处理 Enum 类型
                if hasattr(defect_type, 'value'):
                    defect_type = defect_type.value
                defect_length_cm = getattr(d, "defect_length_cm", None) or 0.0
                defect_id = getattr(d, "id", None)

            score = self.score_defect(defect_type, defect_length_cm)
            total_points += score
            distribution[f"{score}分"] += 1

            per_defect_scores.append(DefectScore(
                defect_id=defect_id,
                defect_type=defect_type,
                defect_length_cm=defect_length_cm,
                point_score=score,
                reason=self._get_score_reason(defect_type, defect_length_cm, score),
            ))

        # 计算每百平方码罚分
        points_per_100sqyd = self._calc_points_per_100sqyd(
            total_points, roll_length_m, roll_width_cm
        )

        result.total_points = total_points
        result.points_per_100sqyd = round(points_per_100sqyd, 2)
        result.grade = self.determine_grade(points_per_100sqyd)
        result.is_pass = points_per_100sqyd <= self.pass_threshold
        result.score_distribution = distribution
        result.per_defect_scores = per_defect_scores
        result.total_defects = len(defects)

        return result

    def determine_grade(self, points_per_100sqyd: float) -> str:
        """
        根据每百平方码罚分判定等级

        Args:
            points_per_100sqyd: 每百平方码罚分

        Returns:
            等级字符串
        """
        if points_per_100sqyd <= 20:
            return "优等品"
        elif points_per_100sqyd <= 28:
            return "一等品"
        elif points_per_100sqyd <= 40:
            return "二等品"
        else:
            return "不合格"

    def _calc_points_per_100sqyd(
        self,
        total_points: int,
        roll_length_m: float,
        roll_width_cm: float,
    ) -> float:
        """
        计算每百平方码罚分

        公式：(总罚分 × 100 × 36) / (检验长度码 × 布幅英寸)

        Args:
            total_points: 总罚分
            roll_length_m: 布卷长度（米）
            roll_width_cm: 布幅宽度（厘米）

        Returns:
            每百平方码罚分
        """
        if roll_length_m <= 0 or roll_width_cm <= 0:
            return 0.0

        # 米 → 码（1 码 = 0.9144 米）
        length_yards = roll_length_m / 0.9144

        # 厘米 → 英寸
        width_inches = roll_width_cm * _INCH_PER_CM

        denominator = length_yards * width_inches
        if denominator <= 0:
            return 0.0

        return (total_points * 100 * 36) / denominator

    def _get_score_reason(
        self, defect_type: str, defect_length_cm: float, score: int
    ) -> str:
        """生成评分说明"""
        if defect_type.lower() in _HOLE_TYPES:
            return "破洞类缺陷，固定 4 分"

        if defect_length_cm <= 0:
            return "未提供缺陷长度，按最小评分 1 分计"

        length_inch = defect_length_cm * _INCH_PER_CM
        return f"缺陷长度 {defect_length_cm:.1f}cm ({length_inch:.1f}in) → {score} 分"
