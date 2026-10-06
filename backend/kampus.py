"""
Kampüs sınırı — herkese açık uçlarda kampüs dışındaki konumlar gösterilmez.

Atmotube cihazları eve/yola götürüldüğünde bulut toplayıcı o konumları da kaydeder. Bunlar ekip üyelerinin
ev ve yol konumları olabilir (KVKK) ve kampüs ortalamalarını bozar. Ham arşiv (measurements) olduğu gibi kalır;
harita, ısı haritası, canlı cihazlar, oturum senkronu ve CSV dışa aktarma bu sınırı uygular.

Merkez ve yarıçap: frontend_v2/data/campus.geojson'daki tüm binaları kapsayan alanın merkezi; en uzak bina
~1,06 km, kapı ve kenarlar için 2 km.
"""
import math
from config import CAMPUS_LAT, CAMPUS_LON, CAMPUS_RADIUS_KM

DLAT = CAMPUS_RADIUS_KM / 111.32
DLON = CAMPUS_RADIUS_KM / (111.32 * math.cos(math.radians(CAMPUS_LAT)))


def near(lat, lon) -> bool:
    """Konum kampüs sınırı içinde mi? (konum yoksa False)"""
    if lat is None or lon is None:
        return False
    try:
        dy = (float(lat) - CAMPUS_LAT) * 111.32
        dx = (float(lon) - CAMPUS_LON) * 111.32 * math.cos(math.radians(CAMPUS_LAT))
    except (TypeError, ValueError):
        return False
    return math.hypot(dx, dy) <= CAMPUS_RADIUS_KM


def sql_box(prefix: str = "") -> str:
    """SQL koşulu (dikdörtgen yaklaşımı): kampüs çevresindeki kutuya düşen konumlar.
    Değerler yapılandırmadan gelir; kullanıcı girdisi içermez."""
    return (f"ABS({prefix}lat - {CAMPUS_LAT:.6f}) < {DLAT:.6f} AND "
            f"ABS({prefix}lon - {CAMPUS_LON:.6f}) < {DLON:.6f}")
