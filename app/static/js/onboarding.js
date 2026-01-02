/**
 * Onboarding Tour System - Divar Style
 * سیستم تور راهنمای کاربران به سبک دیوار
 */

class OnboardingTour {
  constructor() {
    this.currentStep = 0;
    this.tour = null;
    this.overlay = null;
    this.tooltip = null;
    this.isActive = false;
    this.tourData = [];
  }

  // Avoid showing the tour on authentication pages (login/OTP)
  isAuthPage() {
    const path = window.location.pathname || '';
    return (
      path.includes('/login') ||
      path.includes('/verify') ||
      path.includes('/auth/')
    );
  }

  init() {
    if (this.isAuthPage()) return;

    // بررسی اینکه آیا تور از sessionStorage باید ادامه یابد
    const tourStep = sessionStorage.getItem('vinor_tour_step');
    const tourData = sessionStorage.getItem('vinor_tour_data');
    
    if (tourStep !== null && tourData) {
      // تور باید ادامه یابد
      this.tourData = JSON.parse(tourData);
      this.currentStep = parseInt(tourStep);
      this.isActive = true;
      
      // تاخیر کوتاه برای اطمینان از لود شدن صفحه
      setTimeout(() => {
        this.createOverlay();
        this.showStep(this.currentStep);
      }, 500);
      
      // پاک کردن sessionStorage
      sessionStorage.removeItem('vinor_tour_step');
      sessionStorage.removeItem('vinor_tour_data');
      return;
    }

    // بررسی اینکه آیا باید تور کامل شروع شود
    const startFullTour = sessionStorage.getItem('vinor_start_full_tour');
    if (startFullTour === 'true') {
      sessionStorage.removeItem('vinor_start_full_tour');
      setTimeout(() => {
        this.startTour(true);
      }, 2000);
      return;
    }

    // بررسی اینکه آیا کاربر قبلاً تور را دیده است
    const hasSeenTour = localStorage.getItem('vinor_onboarding_completed');
    if (!hasSeenTour) {
      // تاخیر کوتاه برای اطمینان از لود شدن صفحه
      setTimeout(() => {
        this.startTour();
      }, 2000);
    }
  }

  startTour(force = false) {
    if (this.isActive && !force) return;
    
    this.isActive = true;
    this.currentStep = 0;
    
    // اگر force است (اجرای مجدد)، تور کامل را اجرا کن
    if (force) {
      this.tourData = this.getFullTour();
      // اگر در صفحه dashboard نیستیم، ابتدا به dashboard برو
      const path = window.location.pathname;
      if (!path.includes('/dashboard') && path !== '/express/partner/' && path !== '/express/partner') {
        // ذخیره تور برای اجرا بعد از redirect
        sessionStorage.setItem('vinor_start_full_tour', 'true');
        window.location.href = '/express/partner/dashboard';
        return;
      }
    } else {
      // تعیین تور بر اساس صفحه فعلی (فقط برای اولین بار)
      const path = window.location.pathname;
      if (path.includes('/dashboard') || path === '/express/partner/' || path === '/express/partner') {
        this.tourData = this.getDashboardTour();
      } else if (path.includes('/lands/') || path.includes('/land_detail')) {
        this.tourData = this.getLandDetailTour();
      } else if (path.includes('/commissions')) {
        this.tourData = this.getCommissionsTour();
      } else if (path.includes('/notes')) {
        this.tourData = this.getNotesTour();
      } else if (path.includes('/profile')) {
        this.tourData = this.getProfileTour();
      } else {
        // تور پیش‌فرض برای داشبورد
        this.tourData = this.getDashboardTour();
      }
    }

    if (this.tourData.length === 0) return;

    this.createOverlay();
    this.showStep(0);
  }

  getDashboardTour() {
    return [
      {
        element: '[data-tour="dashboard-header"]',
        title: 'خوش آمدید! 👋',
        description: 'این پنل همکاران وینور اکسپرس است. در اینجا می‌توانید فایل‌های اختصاص داده شده را مشاهده کنید.',
        position: 'bottom'
      },
      {
        element: '[data-tour="training-bar"]',
        title: 'نوار آموزش',
        description: 'برای یادگیری نحوه کار با پنل، روی این نوار کلیک کنید و آموزش‌های کامل را مشاهده کنید.',
        position: 'bottom'
      },
      {
        element: '[data-tour="land-card"]',
        title: 'کارت فایل',
        description: 'هر کارت یک فایل اختصاص داده شده به شماست. روی کارت کلیک کنید تا جزئیات را ببینید.',
        position: 'top'
      },
      {
        element: '[data-tour="bottom-nav"]',
        title: 'منوی پایین',
        description: 'از این منو می‌توانید به بخش‌های مختلف پنل دسترسی داشته باشید: داشبورد، پورسانت‌ها، یادداشت‌ها و پروفایل.',
        position: 'top'
      }
    ];
  }

  getLandDetailTour() {
    return [
      {
        element: '[data-tour="land-image"]',
        title: 'تصویر فایل',
        description: 'تصویر اصلی فایل را اینجا می‌بینید. می‌توانید گالری تصاویر را هم مشاهده کنید.',
        position: 'bottom'
      },
      {
        element: '[data-tour="land-info"]',
        title: 'اطلاعات فایل',
        description: 'تمام اطلاعات مهم فایل مانند قیمت، اندازه، موقعیت و کمیسیون در این بخش نمایش داده می‌شود.',
        position: 'top'
      },
      {
        element: '[data-tour="transaction-btn"]',
        title: 'دکمه معامله',
        description: 'اگر مشتری پیدا کردید، روی این دکمه کلیک کنید تا وضعیت فایل را به "در حال معامله" تغییر دهید.',
        position: 'top'
      },
      {
        element: '[data-tour="share-btn"]',
        title: 'اشتراک‌گذاری',
        description: 'می‌توانید لینک فایل را با مشتریان به اشتراک بگذارید. با کلیک روی این دکمه، لینک کپی می‌شود.',
        position: 'top'
      },
      {
        element: '[data-tour="contact-btn"]',
        title: 'تماس',
        description: 'برای تماس با مالک فایل، روی این دکمه کلیک کنید.',
        position: 'top'
      }
    ];
  }

  getCommissionsTour() {
    return [
      {
        element: '[data-tour="commissions-stats"]',
        title: 'آمار پورسانت‌ها',
        description: 'در این بخش می‌توانید کل درآمد، درآمد در انتظار و تعداد فروش‌های موفق را مشاهده کنید.',
        position: 'bottom'
      },
      {
        element: '[data-tour="commission-item"]',
        title: 'لیست پورسانت‌ها',
        description: 'تمام پورسانت‌های شما در اینجا نمایش داده می‌شود. وضعیت هر پورسانت (در انتظار، تأیید شده، پرداخت شده) مشخص است.',
        position: 'top'
      }
    ];
  }

  getNotesTour() {
    return [
      {
        element: '[data-tour="notes-input"]',
        title: 'ثبت یادداشت',
        description: 'می‌توانید یادداشت‌های خصوصی برای خودتان ثبت کنید. روی این فیلد کلیک کنید و یادداشت بنویسید.',
        position: 'bottom'
      },
      {
        element: '[data-tour="notes-grid"]',
        title: 'یادداشت‌های شما',
        description: 'تمام یادداشت‌های شما در اینجا نمایش داده می‌شود. می‌توانید هر یادداشت را حذف کنید.',
        position: 'top'
      }
    ];
  }

  getProfileTour() {
    return [
      {
        element: '[data-tour="profile-section"]',
        title: 'پروفایل شما 👤',
        description: 'در این بخش اطلاعات حساب کاربری شما شامل نام، شماره تماس و نقش نمایش داده می‌شود. همچنین می‌توانید از اینجا از حساب خود خارج شوید.',
        position: 'bottom'
      },
      {
        element: '[data-tour="notes-link"]',
        title: 'یادداشت‌های خصوصی 📝',
        description: 'یادداشت‌های شخصی خود را اینجا ثبت و مدیریت کنید. این یادداشت‌ها فقط برای شما قابل مشاهده است و می‌توانید از آن‌ها برای یادآوری اطلاعات مهم استفاده کنید.',
        position: 'top'
      },
      {
        element: '[data-tour="notifications-link"]',
        title: 'اعلان‌ها 🔔',
        description: 'تمام اعلان‌های مهم مانند تایید پورسانت، فایل‌های جدید و پیام‌های سیستم در این بخش نمایش داده می‌شود. تعداد اعلان‌های خوانده نشده روی آیکون نمایش داده می‌شود.',
        position: 'top'
      },
      {
        element: '[data-tour="top-sellers-link"]',
        title: 'فروشنده‌های برتر 🏆',
        description: 'رتبه‌بندی همکاران برتر را مشاهده کنید و ببینید چه کسانی بیشترین فروش را داشته‌اند. این می‌تواند انگیزه‌بخش باشد!',
        position: 'top'
      },
      {
        element: '[data-tour="help-link"]',
        title: 'راهنمای استفاده 📚',
        description: 'اگر سوالی دارید یا می‌خواهید نحوه استفاده از پلتفرم را یاد بگیرید، این بخش را مطالعه کنید. راهنمای کامل استفاده از تمام قابلیت‌ها در اینجا موجود است.',
        position: 'top'
      },
      {
        element: '[data-tour="support-link"]',
        title: 'تماس با پشتیبانی 💬',
        description: 'در صورت بروز مشکل یا نیاز به راهنمایی، می‌توانید از طریق این بخش با تیم پشتیبانی تماس بگیرید. ما همیشه آماده کمک به شما هستیم.',
        position: 'top'
      },
      {
        element: '[data-tour="bottom-nav"]',
        title: 'منوی پایین 📱',
        description: 'از این منو می‌توانید به بخش‌های اصلی پنل دسترسی سریع داشته باشید: فایل‌ها، پورسانت‌ها، اعلان‌ها و پروفایل.',
        position: 'top'
      },
      {
        element: '[data-tour="restart-tour"]',
        title: 'اجرای مجدد تور راهنما 🔄',
        description: 'اگر می‌خواهید دوباره تور راهنما را ببینید یا بخشی از آموزش را مرور کنید، روی این دکمه کلیک کنید. تور از ابتدا شروع می‌شود و تمام بخش‌ها را پوشش می‌دهد.',
        position: 'top'
      }
    ];
  }

  getFullTour() {
    // تور کامل که از dashboard شروع می‌شود و تمام صفحات را پوشش می‌دهد
    return [
      // مرحله 1: Dashboard - معرفی
      {
        element: '[data-tour="dashboard-header"]',
        title: 'خوش آمدید! 👋',
        description: 'این پنل همکاران وینور اکسپرس است. در اینجا می‌توانید فایل‌های اختصاص داده شده را مشاهده کنید.',
        position: 'bottom',
        page: 'dashboard'
      },
      // مرحله 2: نوار آموزش
      {
        element: '[data-tour="training-bar"]',
        title: 'نوار آموزش',
        description: 'برای یادگیری نحوه کار با پنل، روی این نوار کلیک کنید و آموزش‌های کامل را مشاهده کنید.',
        position: 'bottom',
        page: 'dashboard'
      },
      // مرحله 3: کارت فایل
      {
        element: '[data-tour="land-card"]',
        title: 'کارت فایل',
        description: 'هر کارت یک فایل اختصاص داده شده به شماست. روی کارت کلیک کنید تا جزئیات را ببینید.',
        position: 'top',
        page: 'dashboard',
        action: 'click',
        actionMessage: 'لطفاً روی کارت فایل کلیک کنید تا به صفحه جزئیات بروید. بعد از کلیک، تور ادامه می‌یابد.'
      },
      // مرحله 4: جزئیات فایل - تصویر
      {
        element: '[data-tour="land-image"]',
        title: 'تصویر فایل',
        description: 'تصویر اصلی فایل را اینجا می‌بینید. می‌توانید گالری تصاویر را هم مشاهده کنید.',
        position: 'bottom',
        page: 'land_detail',
        waitForElement: true // منتظر بمان تا المنت پیدا شود
      },
      // مرحله 5: اطلاعات فایل
      {
        element: '[data-tour="land-info"]',
        title: 'اطلاعات فایل',
        description: 'تمام اطلاعات مهم فایل مانند قیمت، اندازه، موقعیت و کمیسیون در این بخش نمایش داده می‌شود.',
        position: 'top',
        page: 'land_detail'
      },
      // مرحله 6: دکمه معامله
      {
        element: '[data-tour="transaction-btn"]',
        title: 'دکمه معامله',
        description: 'اگر مشتری پیدا کردید، روی این دکمه کلیک کنید تا وضعیت فایل را به "در حال معامله" تغییر دهید.',
        position: 'top',
        page: 'land_detail'
      },
      // مرحله 7: دکمه اشتراک
      {
        element: '[data-tour="share-btn"]',
        title: 'اشتراک‌گذاری',
        description: 'می‌توانید لینک فایل را با مشتریان به اشتراک بگذارید. با کلیک روی این دکمه، لینک کپی می‌شود.',
        position: 'top',
        page: 'land_detail'
      },
      // مرحله 8: دکمه تماس
      {
        element: '[data-tour="contact-btn"]',
        title: 'تماس',
        description: 'برای تماس با مالک فایل، روی این دکمه کلیک کنید.',
        position: 'top',
        page: 'land_detail',
        action: 'navigate',
        actionMessage: 'حالا به منوی پایین بروید و روی "پورسانت" کلیک کنید. بعد از رفتن به صفحه پورسانت، تور ادامه می‌یابد.',
        nextUrl: '/express/partner/commissions'
      },
      // مرحله 9: پورسانت‌ها - آمار
      {
        element: '[data-tour="commissions-stats"]',
        title: 'آمار پورسانت‌ها',
        description: 'در این بخش می‌توانید کل درآمد، درآمد در انتظار و تعداد فروش‌های موفق را مشاهده کنید.',
        position: 'bottom',
        page: 'commissions'
      },
      // مرحله 10: لیست پورسانت‌ها
      {
        element: '[data-tour="commission-item"]',
        title: 'لیست پورسانت‌ها',
        description: 'تمام پورسانت‌های شما در اینجا نمایش داده می‌شود. وضعیت هر پورسانت (در انتظار، تأیید شده، پرداخت شده) مشخص است.',
        position: 'top',
        page: 'commissions',
        action: 'navigate',
        actionMessage: 'حالا به منوی پایین بروید و روی "یادداشت‌ها" کلیک کنید. بعد از رفتن به صفحه یادداشت‌ها، تور ادامه می‌یابد.',
        nextUrl: '/express/partner/notes'
      },
      // مرحله 11: یادداشت‌ها - ثبت
      {
        element: '[data-tour="notes-input"]',
        title: 'ثبت یادداشت',
        description: 'می‌توانید یادداشت‌های خصوصی برای خودتان ثبت کنید. روی این فیلد کلیک کنید و یادداشت بنویسید.',
        position: 'bottom',
        page: 'notes'
      },
      // مرحله 12: یادداشت‌های شما
      {
        element: '[data-tour="notes-grid"]',
        title: 'یادداشت‌های شما',
        description: 'تمام یادداشت‌های شما در اینجا نمایش داده می‌شود. می‌توانید هر یادداشت را حذف کنید.',
        position: 'top',
        page: 'notes',
        action: 'navigate',
        actionMessage: 'حالا به منوی پایین بروید و روی "من" کلیک کنید. بعد از رفتن به صفحه پروفایل، تور ادامه می‌یابد.',
        nextUrl: '/express/partner/profile'
      },
      // مرحله 13: پروفایل
      {
        element: '[data-tour="profile-section"]',
        title: 'پروفایل شما 👤',
        description: 'در این بخش اطلاعات حساب کاربری شما شامل نام، شماره تماس و نقش نمایش داده می‌شود. همچنین می‌توانید از اینجا از حساب خود خارج شوید.',
        position: 'bottom',
        page: 'profile'
      },
      // مرحله 14: لینک یادداشت‌ها در پروفایل
      {
        element: '[data-tour="notes-link"]',
        title: 'یادداشت‌های خصوصی 📝',
        description: 'یادداشت‌های شخصی خود را اینجا ثبت و مدیریت کنید. این یادداشت‌ها فقط برای شما قابل مشاهده است و می‌توانید از آن‌ها برای یادآوری اطلاعات مهم استفاده کنید.',
        position: 'top',
        page: 'profile'
      },
      // مرحله 15: اعلان‌ها
      {
        element: '[data-tour="notifications-link"]',
        title: 'اعلان‌ها 🔔',
        description: 'تمام اعلان‌های مهم مانند تایید پورسانت، فایل‌های جدید و پیام‌های سیستم در این بخش نمایش داده می‌شود. تعداد اعلان‌های خوانده نشده روی آیکون نمایش داده می‌شود.',
        position: 'top',
        page: 'profile'
      },
      // مرحله 16: فروشنده‌های برتر
      {
        element: '[data-tour="top-sellers-link"]',
        title: 'فروشنده‌های برتر 🏆',
        description: 'رتبه‌بندی همکاران برتر را مشاهده کنید و ببینید چه کسانی بیشترین فروش را داشته‌اند. این می‌تواند انگیزه‌بخش باشد!',
        position: 'top',
        page: 'profile'
      },
      // مرحله 17: راهنما
      {
        element: '[data-tour="help-link"]',
        title: 'راهنمای استفاده 📚',
        description: 'اگر سوالی دارید یا می‌خواهید نحوه استفاده از پلتفرم را یاد بگیرید، این بخش را مطالعه کنید. راهنمای کامل استفاده از تمام قابلیت‌ها در اینجا موجود است.',
        position: 'top',
        page: 'profile'
      },
      // مرحله 18: پشتیبانی
      {
        element: '[data-tour="support-link"]',
        title: 'تماس با پشتیبانی 💬',
        description: 'در صورت بروز مشکل یا نیاز به راهنمایی، می‌توانید از طریق این بخش با تیم پشتیبانی تماس بگیرید. ما همیشه آماده کمک به شما هستیم.',
        position: 'top',
        page: 'profile'
      },
      // مرحله 19: منوی پایین
      {
        element: '[data-tour="bottom-nav"]',
        title: 'منوی پایین 📱',
        description: 'از این منو می‌توانید به بخش‌های اصلی پنل دسترسی سریع داشته باشید: فایل‌ها، پورسانت‌ها، اعلان‌ها و پروفایل.',
        position: 'top',
        page: 'profile'
      },
      // مرحله 20: اجرای مجدد تور
      {
        element: '[data-tour="restart-tour"]',
        title: 'اجرای مجدد تور راهنما 🔄',
        description: 'اگر می‌خواهید دوباره تور راهنما را ببینید یا بخشی از آموزش را مرور کنید، روی این دکمه کلیک کنید. تور از ابتدا شروع می‌شود و تمام بخش‌ها را پوشش می‌دهد.',
        position: 'top',
        page: 'profile'
      }
    ];
  }

  createOverlay() {
    // ایجاد overlay
    this.overlay = document.createElement('div');
    this.overlay.className = 'onboarding-overlay';
    this.overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      z-index: 9998;
      transition: opacity 0.3s;
    `;
    document.body.appendChild(this.overlay);

    // ایجاد tooltip (موبایل محور)
    const isMobile = window.innerWidth < 640;
    this.tooltip = document.createElement('div');
    this.tooltip.className = 'onboarding-tooltip';
    this.tooltip.style.cssText = `
      position: fixed;
      z-index: 9999;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: ${isMobile ? '16px' : '12px'};
      padding: ${isMobile ? '20px 16px' : '16px'};
      max-width: ${isMobile ? 'calc(100vw - 16px)' : '320px'};
      min-width: ${isMobile ? 'calc(100vw - 16px)' : '280px'};
      width: ${isMobile ? 'calc(100vw - 16px)' : 'auto'};
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 4px 6px -2px rgba(0, 0, 0, 0.1);
      font-family: 'Vazirmatn', sans-serif;
      direction: rtl;
      opacity: 0;
      transform: scale(0.95);
      transition: opacity 0.3s ease, transform 0.3s ease;
      animation: tooltipFadeIn 0.3s ease forwards;
    `;
    // اضافه کردن کلاس dark mode
    if (document.documentElement.classList.contains('dark')) {
      this.tooltip.style.background = '#111827';
      this.tooltip.style.borderColor = '#374151';
      this.tooltip.style.color = '#f9fafb';
    }
    
    // اضافه کردن استایل انیمیشن (موبایل محور)
    if (!document.getElementById('onboarding-animations')) {
      const style = document.createElement('style');
      style.id = 'onboarding-animations';
      style.textContent = `
        @keyframes tooltipFadeIn {
          from {
            opacity: 0;
            transform: scale(0.95) translateY(-10px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateY(0);
          }
        }
        @keyframes highlightPulse {
          0%, 100% {
            outline-color: #2563EB;
          }
          50% {
            outline-color: #3B82F6;
          }
        }
        .onboarding-highlight {
          animation: highlightPulse 2s ease-in-out infinite;
        }
        /* استایل‌های موبایل */
        @media (max-width: 640px) {
          .onboarding-tooltip {
            max-width: calc(100vw - 16px) !important;
            min-width: calc(100vw - 16px) !important;
            width: calc(100vw - 16px) !important;
            padding: 20px 16px !important;
            border-radius: 16px !important;
            font-size: 14px !important;
          }
          .onboarding-tooltip h3 {
            font-size: 16px !important;
            margin-bottom: 8px !important;
          }
          .onboarding-tooltip p {
            font-size: 14px !important;
            line-height: 1.6 !important;
          }
          .onboarding-tooltip button {
            padding: 12px 16px !important;
            font-size: 14px !important;
            min-height: 44px !important;
            touch-action: manipulation;
          }
          .onboarding-tooltip .fa-times {
            font-size: 16px !important;
          }
          .onboarding-overlay {
            background: rgba(0, 0, 0, 0.6) !important;
          }
        }
        /* بهبود touch targets برای موبایل */
        @media (pointer: coarse) {
          .onboarding-tooltip button {
            min-height: 44px;
            min-width: 44px;
          }
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(this.tooltip);
  }

  showStep(index) {
    if (index >= this.tourData.length) {
      this.completeTour();
      return;
    }

    this.currentStep = index;
    const step = this.tourData[index];
    
    // بررسی اینکه آیا در صفحه صحیح هستیم
    if (step.page) {
      const currentPath = window.location.pathname;
      const expectedPath = this.getExpectedPath(step.page);
      const isOnCorrectPage = this.isOnCorrectPage(currentPath, step.page);
      
      if (!isOnCorrectPage) {
        // باید به صفحه صحیح redirect کنیم
        sessionStorage.setItem('vinor_tour_step', index.toString());
        sessionStorage.setItem('vinor_tour_data', JSON.stringify(this.tourData));
        window.location.href = expectedPath;
        return;
      }
    }

    let element = document.querySelector(step.element);
    
    // اگر المنت پیدا نشد و waitForElement فعال است، منتظر بمان
    if (!element && step.waitForElement) {
      let attempts = 0;
      const maxAttempts = 20; // 10 ثانیه
      const checkElement = setInterval(() => {
        element = document.querySelector(step.element);
        attempts++;
        if (element || attempts >= maxAttempts) {
          clearInterval(checkElement);
          if (!element) {
            // اگر بعد از 10 ثانیه هم پیدا نشد، به مرحله بعد برو
            this.showStep(index + 1);
            return;
          }
          // المنت پیدا شد، ادامه بده
          this.showStep(index);
        }
      }, 500);
      return;
    }

    if (!element) {
      // اگر المنت پیدا نشد، به مرحله بعد برو
      setTimeout(() => this.showStep(index + 1), 500);
      return;
    }

    // محاسبه موقعیت
    const rect = element.getBoundingClientRect();
    const position = this.calculatePosition(rect, step.position);

    // تنظیم tooltip
    let actionHtml = '';
    if (step.action === 'click') {
      actionHtml = `<div class="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded text-xs text-blue-700 dark:text-blue-300">${step.actionMessage || 'لطفاً روی المنت کلیک کنید.'}</div>`;
    } else if (step.action === 'navigate') {
      actionHtml = `<div class="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded text-xs text-blue-700 dark:text-blue-300">${step.actionMessage || 'لطفاً به صفحه بعدی بروید.'}</div>`;
    }

    // بررسی dark mode
    const isDark = document.documentElement.classList.contains('dark');
    const bgColor = isDark ? '#111827' : 'white';
    const textColor = isDark ? '#f9fafb' : '#111827';
    const borderColor = isDark ? '#374151' : '#e5e7eb';
    const textSecondary = isDark ? '#d1d5db' : '#4b5563';

    this.tooltip.style.background = bgColor;
    this.tooltip.style.borderColor = borderColor;
    this.tooltip.style.color = textColor;

    const isMobile = window.innerWidth < 640;
    const closeButtonSize = isMobile ? 'w-9 h-9' : 'w-7 h-7';
    const closeButtonIconSize = isMobile ? 'text-sm' : 'text-xs';
    const titleSize = isMobile ? 'text-lg' : 'text-base';
    const descSize = isMobile ? 'text-base' : 'text-sm';
    const buttonPadding = isMobile ? 'px-4 py-2.5' : 'px-3 py-1.5';
    const buttonTextSize = isMobile ? 'text-sm' : 'text-xs';
    const counterTextSize = isMobile ? 'text-sm' : 'text-xs';
    
    this.tooltip.innerHTML = `
      <div class="relative">
        <!-- دکمه بستن -->
        <button onclick="window.onboardingTour.closeTour()" 
                class="absolute top-0 left-0 ${closeButtonSize} flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 active:bg-gray-200 dark:active:bg-gray-700 transition-colors touch-manipulation"
                style="color: ${textSecondary}"
                aria-label="بستن تور">
          <i class="fas fa-times ${closeButtonIconSize}"></i>
        </button>
        <div class="mb-4 ${isMobile ? 'pr-10' : 'pr-7'}">
          <h3 class="${titleSize} font-semibold mb-2" style="color: ${textColor}">${step.title}</h3>
          <p class="${descSize} leading-relaxed" style="color: ${textSecondary}">${step.description}</p>
          ${actionHtml}
        </div>
      </div>
      <div class="flex items-center justify-between gap-2 pt-3" style="border-top: 1px solid ${borderColor}">
        <div class="${counterTextSize} font-medium" style="color: ${textSecondary}">
          ${index + 1} از ${this.tourData.length}
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          ${index > 0 ? `
            <button onclick="window.onboardingTour.prevStep()" class="${buttonPadding} ${buttonTextSize} font-medium border rounded-lg hover:opacity-80 active:opacity-60 transition touch-manipulation" style="border-color: ${borderColor}; color: ${textColor}; min-height: ${isMobile ? '44px' : 'auto'}">
              قبلی
            </button>
          ` : ''}
          ${step.action === 'navigate' && step.nextUrl ? `
            <button onclick="window.onboardingTour.navigateToNext('${step.nextUrl}')" class="${buttonPadding} ${buttonTextSize} font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-800 transition touch-manipulation" style="min-height: ${isMobile ? '44px' : 'auto'}">
              برو به صفحه بعدی
            </button>
          ` : step.action === 'click' ? `
            <button onclick="window.onboardingTour.nextStep()" class="${buttonPadding} ${buttonTextSize} font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-800 transition opacity-50 cursor-not-allowed touch-manipulation" disabled style="min-height: ${isMobile ? '44px' : 'auto'}">
              روی المنت کلیک کنید
            </button>
          ` : `
            <button onclick="window.onboardingTour.nextStep()" class="${buttonPadding} ${buttonTextSize} font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 active:bg-blue-800 transition touch-manipulation" style="min-height: ${isMobile ? '44px' : 'auto'}">
              ${index === this.tourData.length - 1 ? 'پایان' : 'بعدی'}
            </button>
          `}
        </div>
      </div>
    `;

    this.tooltip.style.left = position.left + 'px';
    this.tooltip.style.top = position.top + 'px';
    if (position.width) {
      this.tooltip.style.width = position.width + 'px';
      this.tooltip.style.maxWidth = position.width + 'px';
    }

    // ایجاد highlight برای المنت
    this.highlightElement(element);

    // اگر action === 'click' است، listener برای کلیک اضافه کن
    if (step.action === 'click') {
      const clickHandler = (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        // حذف listener
        element.removeEventListener('click', clickHandler);
        
        // اگر المنت یک لینک یا دکمه است، href را بگیر
        let targetUrl = null;
        if (element.tagName === 'A') {
          targetUrl = element.getAttribute('href');
        } else if (element.getAttribute('data-href')) {
          targetUrl = element.getAttribute('data-href');
        } else {
          // اگر المنت یک کارت است، href را از data-href بگیر
          const cardLink = element.closest('[data-href]');
          if (cardLink) {
            targetUrl = cardLink.getAttribute('data-href');
          }
        }

        if (targetUrl) {
          // ذخیره وضعیت تور
          sessionStorage.setItem('vinor_tour_step', (index + 1).toString());
          sessionStorage.setItem('vinor_tour_data', JSON.stringify(this.tourData));
          // رفتن به صفحه بعدی
          window.location.href = targetUrl;
        } else {
          // اگر href پیدا نشد، به مرحله بعد برو
          setTimeout(() => {
            this.nextStep();
          }, 500);
        }
      };
      
      // اضافه کردن listener
      element.addEventListener('click', clickHandler, { once: true });
      
      // اگر المنت یک کارت است، روی کل کارت listener اضافه کن
      const card = element.closest('[data-href]');
      if (card && card !== element) {
        card.addEventListener('click', clickHandler, { once: true });
      }
    }
  }

  getExpectedPath(page) {
    const paths = {
      'dashboard': '/express/partner/dashboard',
      'land_detail': '/express/partner/lands',
      'commissions': '/express/partner/commissions',
      'notes': '/express/partner/notes',
      'profile': '/express/partner/profile'
    };
    return paths[page] || '/express/partner/dashboard';
  }

  isOnCorrectPage(currentPath, expectedPage) {
    if (expectedPage === 'dashboard') {
      return currentPath.includes('/dashboard') || currentPath === '/express/partner/' || currentPath === '/express/partner';
    } else if (expectedPage === 'land_detail') {
      return currentPath.includes('/lands/') || currentPath.includes('/land_detail');
    } else if (expectedPage === 'commissions') {
      return currentPath.includes('/commissions');
    } else if (expectedPage === 'notes') {
      return currentPath.includes('/notes');
    } else if (expectedPage === 'profile') {
      return currentPath.includes('/profile');
    }
    return true;
  }

  navigateToNext(url) {
    sessionStorage.setItem('vinor_tour_step', (this.currentStep + 1).toString());
    sessionStorage.setItem('vinor_tour_data', JSON.stringify(this.tourData));
    window.location.href = url;
  }

  calculatePosition(rect, position) {
    // محاسبه اندازه tooltip بر اساس محتوا (موبایل محور)
    const isMobile = window.innerWidth < 640;
    const tooltipMaxWidth = isMobile ? window.innerWidth - 16 : Math.min(320, window.innerWidth - 32);
    const tooltipMinWidth = isMobile ? window.innerWidth - 16 : 280;
    const tooltipWidth = Math.max(tooltipMinWidth, tooltipMaxWidth);
    const tooltipHeight = isMobile ? Math.min(300, window.innerHeight * 0.5) : Math.min(250, window.innerHeight * 0.4);
    const padding = isMobile ? 8 : 16;
    const actualPadding = padding;
    let left, top;

    switch (position) {
      case 'top':
        if (isMobile) {
          // در موبایل tooltip را در وسط صفحه قرار بده
          left = actualPadding;
          top = Math.max(actualPadding, (window.innerHeight - tooltipHeight) / 2);
        } else {
          left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
          top = rect.top - tooltipHeight - actualPadding;
          // اگر فضا برای بالا نیست، به پایین ببر
          if (top < actualPadding) {
            top = rect.bottom + actualPadding;
          }
        }
        break;
      case 'bottom':
        if (isMobile) {
          // در موبایل tooltip را در پایین صفحه قرار بده
          left = actualPadding;
          top = window.innerHeight - tooltipHeight - actualPadding - 80; // فاصله از bottom nav
        } else {
          left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
          top = rect.bottom + actualPadding;
          // اگر فضا برای پایین نیست، به بالا ببر
          if (top + tooltipHeight > window.innerHeight - actualPadding) {
            top = rect.top - tooltipHeight - actualPadding;
          }
        }
        break;
      case 'left':
        left = rect.left - tooltipWidth - actualPadding;
        top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
        // اگر فضا برای چپ نیست، به راست ببر
        if (left < actualPadding) {
          left = rect.right + actualPadding;
        }
        break;
      case 'right':
        left = rect.right + actualPadding;
        top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
        // اگر فضا برای راست نیست، به چپ ببر
        if (left + tooltipWidth > window.innerWidth - actualPadding) {
          left = rect.left - tooltipWidth - actualPadding;
        }
        break;
      default:
        left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        top = rect.bottom + actualPadding;
    }

    // اطمینان از اینکه tooltip در viewport است (با در نظر گیری responsive)
    if (left < actualPadding) left = actualPadding;
    if (left + tooltipWidth > window.innerWidth - actualPadding) {
      left = window.innerWidth - tooltipWidth - actualPadding;
    }
    if (top < actualPadding) top = actualPadding;
    if (top + tooltipHeight > window.innerHeight - actualPadding) {
      top = window.innerHeight - tooltipHeight - actualPadding;
    }

    return { left, top, width: tooltipWidth };
  }

  highlightElement(element) {
    // حذف highlight قبلی
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
      el.classList.remove('onboarding-highlight');
      el.style.outline = '';
      el.style.outlineOffset = '';
    });

    // اضافه کردن highlight با انیمیشن
    element.classList.add('onboarding-highlight');
    element.style.outline = '3px solid #2563EB';
    element.style.outlineOffset = '4px';
    element.style.zIndex = '9999';
    element.style.position = 'relative';
    element.style.transition = 'outline-color 0.3s ease';
    
    // اضافه کردن backdrop برای بهتر دیده شدن
    if (!document.querySelector('.onboarding-backdrop')) {
      const backdrop = document.createElement('div');
      backdrop.className = 'onboarding-backdrop';
      backdrop.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(37, 99, 235, 0.1);
        z-index: 9997;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.3s ease;
      `;
      document.body.appendChild(backdrop);
      setTimeout(() => {
        backdrop.style.opacity = '1';
      }, 10);
    }

    // اسکرول به المنت (بهینه برای موبایل)
    const isMobile = window.innerWidth < 640;
    if (isMobile) {
      // در موبایل با offset بیشتر اسکرول کن تا tooltip دیده شود
      const elementTop = element.getBoundingClientRect().top + window.pageYOffset;
      const offset = 100; // فاصله از بالا برای نمایش tooltip
      window.scrollTo({
        top: elementTop - offset,
        behavior: 'smooth'
      });
    } else {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  nextStep() {
    // حذف highlight
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
      el.classList.remove('onboarding-highlight');
      el.style.outline = '';
      el.style.outlineOffset = '';
      el.style.zIndex = '';
      el.style.position = '';
      el.style.transition = '';
    });

    this.showStep(this.currentStep + 1);
  }

  prevStep() {
    // حذف highlight
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
      el.classList.remove('onboarding-highlight');
      el.style.outline = '';
      el.style.outlineOffset = '';
      el.style.zIndex = '';
      el.style.position = '';
      el.style.transition = '';
    });

    if (this.currentStep > 0) {
      this.showStep(this.currentStep - 1);
    }
  }

  closeTour() {
    // بستن تور بدون ذخیره کردن completion (کاربر می‌تواند دوباره ببیند)
    this.completeTour(false);
  }

  completeTour(saveCompletion = true) {
    // ذخیره اینکه کاربر تور را دیده است (فقط اگر saveCompletion true باشد)
    if (saveCompletion) {
      localStorage.setItem('vinor_onboarding_completed', 'true');
    }
    
    // حذف backdrop
    const backdrop = document.querySelector('.onboarding-backdrop');
    if (backdrop) {
      backdrop.style.opacity = '0';
      setTimeout(() => backdrop.remove(), 300);
    }
    
    // حذف overlay و tooltip با انیمیشن
    if (this.overlay) {
      this.overlay.style.opacity = '0';
      setTimeout(() => this.overlay.remove(), 300);
    }
    if (this.tooltip) {
      this.tooltip.style.opacity = '0';
      this.tooltip.style.transform = 'scale(0.95) translateY(-10px)';
      setTimeout(() => this.tooltip.remove(), 300);
    }

    // حذف highlight
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
      el.classList.remove('onboarding-highlight');
      el.style.outline = '';
      el.style.outlineOffset = '';
      el.style.zIndex = '';
      el.style.position = '';
      el.style.transition = '';
    });

    // پاک کردن sessionStorage برای تور در حال اجرا
    sessionStorage.removeItem('vinor_tour_step');
    sessionStorage.removeItem('vinor_tour_data');
    sessionStorage.removeItem('vinor_start_full_tour');

    this.isActive = false;
  }

  restartTour() {
    localStorage.removeItem('vinor_onboarding_completed');
    // شروع تور کامل از dashboard
    const path = window.location.pathname;
    if (!path.includes('/dashboard') && path !== '/express/partner/' && path !== '/express/partner') {
      sessionStorage.setItem('vinor_start_full_tour', 'true');
      window.location.href = '/express/partner/dashboard';
    } else {
      this.startTour(true);
    }
  }
}

// ایجاد instance جهانی
window.onboardingTour = new OnboardingTour();

// شروع خودکار تور فقط پس از لود کامل صفحه
if (document.readyState === 'complete') {
  window.onboardingTour.init();
} else {
  window.addEventListener('load', () => window.onboardingTour.init(), { once: true });
}

