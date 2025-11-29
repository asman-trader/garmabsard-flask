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

  init() {
    // بررسی اینکه آیا کاربر قبلاً تور را دیده است
    const hasSeenTour = localStorage.getItem('vinor_onboarding_completed');
    if (!hasSeenTour) {
      // تاخیر کوتاه برای اطمینان از لود شدن صفحه
      setTimeout(() => {
        this.startTour();
      }, 1000);
    }
  }

  startTour(force = false) {
    if (this.isActive && !force) return;
    
    this.isActive = true;
    this.currentStep = 0;
    
    // تعیین تور بر اساس صفحه فعلی
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
        title: 'پروفایل شما',
        description: 'اطلاعات حساب کاربری شما در این بخش نمایش داده می‌شود.',
        position: 'bottom'
      },
      {
        element: '[data-tour="notes-link"]',
        title: 'یادداشت‌ها',
        description: 'برای مشاهده و مدیریت یادداشت‌های خصوصی خود، اینجا کلیک کنید.',
        position: 'top'
      },
      {
        element: '[data-tour="support-link"]',
        title: 'پشتیبانی',
        description: 'در صورت نیاز به راهنمایی یا پشتیبانی، می‌توانید از این بخش با ما تماس بگیرید.',
        position: 'top'
      },
      {
        element: '[data-tour="restart-tour"]',
        title: 'اجرای مجدد تور',
        description: 'اگر می‌خواهید دوباره تور راهنما را ببینید، روی این دکمه کلیک کنید.',
        position: 'top'
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

    // ایجاد tooltip
    this.tooltip = document.createElement('div');
    this.tooltip.className = 'onboarding-tooltip';
    this.tooltip.style.cssText = `
      position: fixed;
      z-index: 9999;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 16px;
      max-width: 320px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      font-family: 'Vazirmatn', sans-serif;
      direction: rtl;
    `;
    document.body.appendChild(this.tooltip);
  }

  showStep(index) {
    if (index >= this.tourData.length) {
      this.completeTour();
      return;
    }

    this.currentStep = index;
    const step = this.tourData[index];
    const element = document.querySelector(step.element);

    if (!element) {
      // اگر المنت پیدا نشد، به مرحله بعد برو
      this.showStep(index + 1);
      return;
    }

    // محاسبه موقعیت
    const rect = element.getBoundingClientRect();
    const position = this.calculatePosition(rect, step.position);

    // تنظیم tooltip
    this.tooltip.innerHTML = `
      <div class="mb-3">
        <h3 class="text-base font-semibold text-gray-900 mb-1">${step.title}</h3>
        <p class="text-sm text-gray-600 leading-relaxed">${step.description}</p>
      </div>
      <div class="flex items-center justify-between gap-2 pt-2 border-t border-gray-200">
        <div class="text-xs text-gray-500">
          ${index + 1} از ${this.tourData.length}
        </div>
        <div class="flex items-center gap-2">
          ${index > 0 ? `
            <button onclick="window.onboardingTour.prevStep()" class="px-3 py-1.5 text-xs font-medium border border-gray-300 rounded-lg hover:bg-gray-50 transition">
              قبلی
            </button>
          ` : ''}
          <button onclick="window.onboardingTour.nextStep()" class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            ${index === this.tourData.length - 1 ? 'پایان' : 'بعدی'}
          </button>
        </div>
      </div>
    `;

    this.tooltip.style.left = position.left + 'px';
    this.tooltip.style.top = position.top + 'px';

    // ایجاد highlight برای المنت
    this.highlightElement(element);
  }

  calculatePosition(rect, position) {
    const tooltipWidth = 320;
    const tooltipHeight = 200;
    const padding = 16;
    let left, top;

    switch (position) {
      case 'top':
        left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        top = rect.top - tooltipHeight - padding;
        break;
      case 'bottom':
        left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        top = rect.bottom + padding;
        break;
      case 'left':
        left = rect.left - tooltipWidth - padding;
        top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
        break;
      case 'right':
        left = rect.right + padding;
        top = rect.top + (rect.height / 2) - (tooltipHeight / 2);
        break;
      default:
        left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        top = rect.bottom + padding;
    }

    // اطمینان از اینکه tooltip در viewport است
    if (left < padding) left = padding;
    if (left + tooltipWidth > window.innerWidth - padding) {
      left = window.innerWidth - tooltipWidth - padding;
    }
    if (top < padding) top = padding;
    if (top + tooltipHeight > window.innerHeight - padding) {
      top = window.innerHeight - tooltipHeight - padding;
    }

    return { left, top };
  }

  highlightElement(element) {
    // حذف highlight قبلی
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
      el.classList.remove('onboarding-highlight');
      el.style.outline = '';
      el.style.outlineOffset = '';
    });

    // اضافه کردن highlight
    element.classList.add('onboarding-highlight');
    element.style.outline = '3px solid #2563EB';
    element.style.outlineOffset = '4px';
    element.style.zIndex = '9999';
    element.style.position = 'relative';

    // اسکرول به المنت
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  nextStep() {
    // حذف highlight
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
      el.classList.remove('onboarding-highlight');
      el.style.outline = '';
      el.style.outlineOffset = '';
      el.style.zIndex = '';
      el.style.position = '';
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
    });

    if (this.currentStep > 0) {
      this.showStep(this.currentStep - 1);
    }
  }

  completeTour() {
    // ذخیره اینکه کاربر تور را دیده است
    localStorage.setItem('vinor_onboarding_completed', 'true');
    
    // حذف overlay و tooltip
    if (this.overlay) {
      this.overlay.remove();
    }
    if (this.tooltip) {
      this.tooltip.remove();
    }

    // حذف highlight
    document.querySelectorAll('.onboarding-highlight').forEach(el => {
      el.classList.remove('onboarding-highlight');
      el.style.outline = '';
      el.style.outlineOffset = '';
      el.style.zIndex = '';
      el.style.position = '';
    });

    this.isActive = false;
  }

  restartTour() {
    localStorage.removeItem('vinor_onboarding_completed');
    this.startTour(true);
  }
}

// ایجاد instance جهانی
window.onboardingTour = new OnboardingTour();

// شروع خودکار تور بعد از لود شدن صفحه
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.onboardingTour.init();
  });
} else {
  window.onboardingTour.init();
}

