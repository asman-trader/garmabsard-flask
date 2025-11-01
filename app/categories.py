# app/categories.py
# ساختار دسته‌بندی جامع برای بازار خرید و فروش مانند دیوار

CATEGORIES = {
    "real_estate": {
        "id": "real_estate",
        "title": "املاک",
        "icon": "fa-home",
        "description": "خرید، فروش یا اجاره واحدهای مسکونی، اداری، تجاری و پروژه‌ها",
        "subcategories": {
            "rent_residential": {
                "title": "اجاره مسکونی",
                "icon": "fa-key",
                "items": ["آپارتمان", "خانه و ویلا"]
            },
            "sale_residential": {
                "title": "فروش مسکونی",
                "icon": "fa-sign-hanging",
                "items": ["آپارتمان", "خانه و ویلا", "زمین و کلنگی"]
            },
            "sale_commercial": {
                "title": "فروش اداری و تجاری",
                "icon": "fa-briefcase",
                "items": ["دفتر کار", "مغازه و غرفه", "صنعتی و کشاورزی"]
            },
            "rent_commercial": {
                "title": "اجاره اداری و تجاری",
                "icon": "fa-building",
                "items": ["دفتر کار", "مغازه", "صنعتی"]
            },
            "short_term_rent": {
                "title": "اجاره کوتاه‌مدت",
                "icon": "fa-clock",
                "items": ["آپارتمان و سوئیت", "ویلا و باغ", "دفتر کار"]
            },
            "construction_project": {
                "title": "پروژه‌های ساخت و ساز",
                "icon": "fa-hammer",
                "items": ["مشارکت در ساخت", "پیش‌فروش"]
            }
        }
    },
    "vehicles": {
        "id": "vehicles",
        "title": "وسایل نقلیه",
        "icon": "fa-car",
        "description": "خودرو، موتورسیکلت و لوازم آن‌ها",
        "subcategories": {
            "cars": {
                "title": "خودرو",
                "icon": "fa-car-side",
                "items": ["سواری و وانت", "کلاسیک", "اجاره‌ای", "سنگین"]
            },
            "parts": {
                "title": "قطعات و لوازم جانبی",
                "icon": "fa-cog",
                "items": []
            },
            "motorcycle": {
                "title": "موتورسیکلت",
                "icon": "fa-motorcycle",
                "items": []
            },
            "boat_other": {
                "title": "قایق و سایر وسایل نقلیه",
                "icon": "fa-ship",
                "items": []
            }
        }
    },
    "digital": {
        "id": "digital",
        "title": "کالای دیجیتال",
        "icon": "fa-laptop",
        "description": "موبایل، رایانه، کنسول، صوتی و تصویری",
        "subcategories": {
            "mobile_tablet": {
                "title": "موبایل و تبلت",
                "icon": "fa-mobile-alt",
                "items": ["موبایل", "تبلت", "لوازم جانبی", "سیم‌کارت"]
            },
            "computer": {
                "title": "رایانه",
                "icon": "fa-desktop",
                "items": ["لپ‌تاپ", "دسکتاپ", "قطعات", "مودم", "پرینتر"]
            },
            "gaming": {
                "title": "کنسول و بازی",
                "icon": "fa-gamepad",
                "items": []
            },
            "audio_video": {
                "title": "صوتی و تصویری",
                "icon": "fa-tv",
                "items": ["تلویزیون", "دوربین", "سیستم صوتی", "فیلم و موسیقی"]
            }
        }
    },
    "home_kitchen": {
        "id": "home_kitchen",
        "title": "خانه و آشپزخانه",
        "icon": "fa-couch",
        "description": "وسایل خانه، تزئینات و ابزار",
        "subcategories": {
            "appliances": {
                "title": "لوازم خانگی برقی",
                "icon": "fa-refrigerator",
                "items": ["یخچال", "لباسشویی", "جاروبرقی", "اجاق گاز"]
            },
            "kitchenware": {
                "title": "ظروف و لوازم آشپزخانه",
                "icon": "fa-utensils",
                "items": []
            },
            "furniture": {
                "title": "مبلمان و صنایع چوب",
                "icon": "fa-chair",
                "items": []
            },
            "lighting": {
                "title": "نور و روشنایی",
                "icon": "fa-lightbulb",
                "items": []
            },
            "carpet": {
                "title": "فرش و موکت",
                "icon": "fa-th",
                "items": []
            },
            "bedding": {
                "title": "تشک و رختخواب",
                "icon": "fa-bed",
                "items": []
            },
            "decorative": {
                "title": "لوازم دکوری",
                "icon": "fa-palette",
                "items": []
            },
            "heating_cooling": {
                "title": "تهویه و گرمایش",
                "icon": "fa-snowflake",
                "items": []
            },
            "cleaning": {
                "title": "شست‌وشو و نظافت",
                "icon": "fa-spray-can",
                "items": []
            }
        }
    },
    "services": {
        "id": "services",
        "title": "خدمات",
        "icon": "fa-tools",
        "description": "ارائه خدمات مختلف به مردم",
        "subcategories": {
            "vehicle_service": {
                "title": "موتور و ماشین",
                "icon": "fa-wrench",
                "items": []
            },
            "catering": {
                "title": "پذیرایی و مراسم",
                "icon": "fa-birthday-cake",
                "items": []
            },
            "tech_service": {
                "title": "خدمات رایانه‌ای و موبایل",
                "icon": "fa-laptop-code",
                "items": []
            },
            "financial": {
                "title": "مالی و بیمه",
                "icon": "fa-money-bill",
                "items": []
            },
            "transport": {
                "title": "حمل و نقل",
                "icon": "fa-truck",
                "items": []
            },
            "craft": {
                "title": "پیشه و مهارت",
                "icon": "fa-hammer",
                "items": []
            },
            "beauty": {
                "title": "آرایشگری و زیبایی",
                "icon": "fa-cut",
                "items": []
            },
            "cleaning_service": {
                "title": "نظافت",
                "icon": "fa-broom",
                "items": []
            },
            "gardening": {
                "title": "باغبانی",
                "icon": "fa-leaf",
                "items": []
            },
            "education": {
                "title": "آموزشی",
                "icon": "fa-graduation-cap",
                "items": []
            }
        }
    },
    "personal": {
        "id": "personal",
        "title": "وسایل شخصی",
        "icon": "fa-user",
        "description": "لوازم فردی و پوشاک",
        "subcategories": {
            "clothing": {
                "title": "کیف، کفش و لباس",
                "icon": "fa-tshirt",
                "items": []
            },
            "jewelry": {
                "title": "زیورآلات و ساعت",
                "icon": "fa-gem",
                "items": []
            },
            "cosmetics": {
                "title": "آرایشی و بهداشتی",
                "icon": "fa-spa",
                "items": []
            },
            "kids_toys": {
                "title": "وسایل بچه و اسباب‌بازی",
                "icon": "fa-child",
                "items": []
            },
            "stationery": {
                "title": "لوازم‌التحریر",
                "icon": "fa-pen",
                "items": []
            }
        }
    },
    "entertainment": {
        "id": "entertainment",
        "title": "سرگرمی و فراغت",
        "icon": "fa-gamepad",
        "description": "فعالیت‌های تفریحی و فرهنگی",
        "subcategories": {
            "tickets": {
                "title": "بلیت",
                "icon": "fa-ticket-alt",
                "items": ["کنسرت", "سینما", "مسابقه", "تور"]
            },
            "books": {
                "title": "کتاب و مجله",
                "icon": "fa-book",
                "items": []
            },
            "bicycle": {
                "title": "دوچرخه و اسکوتر",
                "icon": "fa-bicycle",
                "items": []
            },
            "pets": {
                "title": "حیوانات و لوازم آن‌ها",
                "icon": "fa-paw",
                "items": []
            },
            "collection": {
                "title": "کلکسیون و اشیای قدیمی",
                "icon": "fa-archive",
                "items": []
            },
            "music_instruments": {
                "title": "آلات موسیقی",
                "icon": "fa-guitar",
                "items": []
            },
            "sports": {
                "title": "ورزش و تناسب اندام",
                "icon": "fa-dumbbell",
                "items": []
            },
            "toys": {
                "title": "اسباب‌بازی",
                "icon": "fa-cube",
                "items": []
            }
        }
    },
    "social": {
        "id": "social",
        "title": "اجتماعی",
        "icon": "fa-users",
        "description": "رویدادها و اطلاع‌رسانی‌های عمومی",
        "subcategories": {
            "events": {
                "title": "رویداد و همایش",
                "icon": "fa-calendar-alt",
                "items": []
            },
            "volunteer": {
                "title": "فعالیت داوطلبانه",
                "icon": "fa-handshake",
                "items": []
            },
            "research": {
                "title": "تحقیقاتی",
                "icon": "fa-microscope",
                "items": []
            },
            "lost_found": {
                "title": "گم‌شده‌ها",
                "icon": "fa-search",
                "items": ["حیوانات", "اشیاء"]
            }
        }
    },
    "industrial": {
        "id": "industrial",
        "title": "تجهیزات و صنعتی",
        "icon": "fa-industry",
        "description": "ویژهٔ مشاغل و تولیدکنندگان",
        "subcategories": {
            "construction_materials": {
                "title": "مصالح و تجهیزات ساختمان",
                "icon": "fa-building",
                "items": []
            },
            "tools": {
                "title": "ابزارآلات",
                "icon": "fa-toolbox",
                "items": []
            },
            "machinery": {
                "title": "ماشین‌آلات صنعتی",
                "icon": "fa-cogs",
                "items": []
            },
            "business_equipment": {
                "title": "تجهیزات کسب‌وکار",
                "icon": "fa-store",
                "items": ["پزشکی", "فروشگاهی", "رستوران", "آرایشگاه", "دفترکار"]
            },
            "wholesale": {
                "title": "عمده‌فروشی",
                "icon": "fa-boxes",
                "items": []
            }
        }
    },
    "jobs": {
        "id": "jobs",
        "title": "استخدام و کاریابی",
        "icon": "fa-briefcase",
        "description": "ثبت آگهی شغلی یا جستجوی کار (غیر رایگان)",
        "is_paid": True,
        "subcategories": {
            "admin": {
                "title": "اداری و مدیریت",
                "icon": "fa-clipboard-list",
                "items": []
            },
            "cleaning_job": {
                "title": "سرایداری و نظافت",
                "icon": "fa-broom",
                "items": []
            },
            "construction_job": {
                "title": "معماری و ساختمان",
                "icon": "fa-hard-hat",
                "items": []
            },
            "retail_job": {
                "title": "فروشگاه و رستوران",
                "icon": "fa-utensils",
                "items": []
            },
            "it_job": {
                "title": "فناوری اطلاعات",
                "icon": "fa-code",
                "items": []
            },
            "legal_finance": {
                "title": "مالی و حقوقی",
                "icon": "fa-balance-scale",
                "items": []
            },
            "marketing_sales": {
                "title": "بازاریابی و فروش",
                "icon": "fa-chart-line",
                "items": []
            },
            "engineering": {
                "title": "صنعتی و مهندسی",
                "icon": "fa-cog",
                "items": []
            },
            "teaching": {
                "title": "آموزشی",
                "icon": "fa-chalkboard-teacher",
                "items": []
            },
            "transport_job": {
                "title": "حمل‌ونقل",
                "icon": "fa-truck",
                "items": []
            },
            "medical": {
                "title": "درمانی و بهداشتی",
                "icon": "fa-user-md",
                "items": []
            },
            "media": {
                "title": "هنری و رسانه",
                "icon": "fa-video",
                "items": []
            }
        }
    }
}

def get_category_by_id(cat_id):
    """Get category by ID"""
    return CATEGORIES.get(cat_id)

def get_all_categories():
    """Get all main categories"""
    return CATEGORIES

def get_subcategory(cat_id, subcat_id):
    """Get subcategory by category ID and subcategory ID"""
    cat = CATEGORIES.get(cat_id)
    if cat:
        return cat.get("subcategories", {}).get(subcat_id)
    return None

