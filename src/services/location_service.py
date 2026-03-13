"""
Location verification service for CampusVoice.

Extracts GPS coordinates from image EXIF metadata and checks whether
the location falls within SREC campus boundaries.

This service NEVER blocks complaint submission — it only sets a
`location_verified` flag that appears as an informational badge.
"""

import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SREC campus boundary polygon
# Source: SREC.kmz (Google My Maps export)
# Format: list of (latitude, longitude) tuples
# ---------------------------------------------------------------------------
_SREC_POLYGON: list[Tuple[float, float]] = [
    (11.0991833, 76.9643718),
    (11.0995457, 76.9653963),
    (11.0991931, 76.9655572),
    (11.0995286, 76.9669908),
    (11.1001577, 76.9668366),
    (11.1006283, 76.9692655),
    (11.1006941, 76.9693808),
    (11.1033946, 76.9690536),
    (11.1031840, 76.9676616),
    (11.1030077, 76.9670943),
    (11.1028432, 76.9659570),
    (11.1027945, 76.9657693),
    (11.1025800, 76.9651993),
    (11.1021036, 76.9641988),
    (11.1015732, 76.9633633),
    (11.0991833, 76.9643718),  # closing point
]

# Bounding box fast-reject (min_lat, max_lat, min_lon, max_lon)
_BBOX = (
    min(p[0] for p in _SREC_POLYGON),
    max(p[0] for p in _SREC_POLYGON),
    min(p[1] for p in _SREC_POLYGON),
    max(p[1] for p in _SREC_POLYGON),
)


def _point_in_polygon(lat: float, lon: float) -> bool:
    """
    Ray-casting point-in-polygon test.

    Returns True if (lat, lon) is inside _SREC_POLYGON.
    """
    # Fast bounding-box reject
    min_lat, max_lat, min_lon, max_lon = _BBOX
    if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
        return False

    poly = _SREC_POLYGON
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > lon) != (yj > lon)) and (lat < (xj - xi) * (lon - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _rational_to_float(rational) -> float:
    """Convert a PIL IFDRational or (numerator, denominator) tuple to float."""
    try:
        # PIL IFDRational — supports direct division
        return float(rational)
    except Exception:
        pass
    try:
        num, den = rational
        return num / den if den != 0 else 0.0
    except Exception:
        return 0.0


def _dms_to_decimal(dms_tuple, ref: str) -> Optional[float]:
    """
    Convert DMS (degrees, minutes, seconds) EXIF tuple + ref to decimal degrees.

    dms_tuple: iterable of 3 IFDRational values — (degrees, minutes, seconds)
    ref: 'N'/'S'/'E'/'W'
    """
    try:
        deg, mins, secs = dms_tuple[0], dms_tuple[1], dms_tuple[2]
        decimal = _rational_to_float(deg) + _rational_to_float(mins) / 60.0 + _rational_to_float(secs) / 3600.0
        if ref in ('S', 'W'):
            decimal = -decimal
        return decimal
    except Exception as e:
        logger.debug(f"DMS conversion failed: {e}")
        return None


def extract_gps_from_image(image_bytes: bytes) -> Optional[Tuple[float, float]]:
    """
    Extract GPS coordinates from image EXIF metadata.

    Returns (latitude, longitude) as decimal degrees, or None if:
    - Image has no EXIF data
    - EXIF has no GPS tags
    - Any parsing error occurs

    All failures are swallowed — this must never break complaint submission.
    """
    try:
        from PIL import Image, ExifTags  # type: ignore
    except ImportError:
        logger.debug("Pillow not available — skipping GPS extraction")
        return None

    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Try modern getexif() first (PIL ≥ 7.0)
        exif_data = None
        try:
            exif_data = img.getexif()
        except AttributeError:
            pass

        # Fallback: _getexif() for JPEG
        if not exif_data:
            try:
                exif_data = img._getexif()  # type: ignore[attr-defined]
            except AttributeError:
                pass

        if not exif_data:
            logger.debug("No EXIF data found in image")
            return None

        # GPS IFD tag is 34853
        GPS_IFD_TAG = 34853
        gps_info = exif_data.get(GPS_IFD_TAG)

        if not gps_info:
            logger.debug("No GPSInfo tag in EXIF")
            return None

        # GPS tag IDs
        GPS_LAT_REF  = 1
        GPS_LAT      = 2
        GPS_LON_REF  = 3
        GPS_LON      = 4

        lat_ref = gps_info.get(GPS_LAT_REF)
        lat_dms = gps_info.get(GPS_LAT)
        lon_ref = gps_info.get(GPS_LON_REF)
        lon_dms = gps_info.get(GPS_LON)

        if not (lat_ref and lat_dms and lon_ref and lon_dms):
            logger.debug("Incomplete GPS tags in EXIF")
            return None

        lat = _dms_to_decimal(lat_dms, lat_ref)
        lon = _dms_to_decimal(lon_dms, lon_ref)

        if lat is None or lon is None:
            return None

        logger.debug(f"Extracted GPS: lat={lat:.6f}, lon={lon:.6f}")
        return (lat, lon)

    except Exception as e:
        logger.debug(f"GPS extraction error (non-fatal): {e}")
        return None


def verify_location_from_coords(lat: float, lon: float) -> bool:
    """
    Check whether a lat/lon coordinate pair falls within SREC campus.

    Used when the frontend provides live GPS coordinates (camera capture path).
    Returns True only if the point is inside the SREC polygon.
    All exceptions are caught — never raises.
    """
    try:
        result = _point_in_polygon(lat, lon)
        if result:
            logger.info(f"Live GPS verified within SREC: ({lat:.6f}, {lon:.6f})")
        else:
            logger.debug(f"Live GPS outside SREC polygon: ({lat:.6f}, {lon:.6f})")
        return result
    except Exception as e:
        logger.debug(f"GPS coords verification error (non-fatal): {e}")
        return False


def verify_location_from_image(image_bytes: bytes) -> bool:
    """
    Check whether an image's GPS metadata places it within SREC campus.

    Returns True only if:
    1. GPS metadata is present in the image
    2. The coordinates fall inside the SREC polygon

    Returns False for any other case (no metadata, outside polygon, errors).
    This function is intentionally silent — all exceptions are caught.
    """
    try:
        coords = extract_gps_from_image(image_bytes)
        if coords is None:
            return False
        lat, lon = coords
        result = _point_in_polygon(lat, lon)
        if result:
            logger.info(f"Location verified within SREC: ({lat:.6f}, {lon:.6f})")
        else:
            logger.debug(f"Location outside SREC polygon: ({lat:.6f}, {lon:.6f})")
        return result
    except Exception as e:
        logger.debug(f"Location verification error (non-fatal): {e}")
        return False
