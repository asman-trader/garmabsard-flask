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
      }, 1000);
      return;
    }

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
        title: 'پروفایل شما',
        description: 'اطلاعات حساب کاربری شما در این بخش نمایش داده می‌شود.',
        position: 'bottom',
        page: 'profile'
      },
      // مرحله 14: لینک یادداشت‌ها در پروفایل
      {
        element: '[data-tour="notes-link"]',
        title: 'دسترسی سریع به یادداشت‌ها',
        description: 'می‌توانید از اینجا به یادداشت‌های خود دسترسی سریع داشته باشید.',
        position: 'top',
        page: 'profile'
      },
      // مرحله 15: پشتیبانی
      {
        element: '[data-tour="support-link"]',
        title: 'پشتیبانی',
        description: 'در صورت نیاز به راهنمایی یا پشتیبانی، می‌توانید از این بخش با ما تماس بگیرید.',
        position: 'top',
        page: 'profile'
      },
      // مرحله 16: منوی پایین
      {
        element: '[data-tour="bottom-nav"]',
        title: 'منوی پایین',
        description: 'از این منو می‌توانید به بخش‌های مختلف پنل دسترسی داشته باشید: فایل‌ها، پورسانت‌ها، اعلان‌ها و پروفایل.',
        position: 'top',
        page: 'profile'
      },
      // مرحله 17: اجرای مجدد تور
      {
        element: '[data-tour="restart-tour"]',
        title: 'اجرای مجدد تور',
        description: 'اگر می‌خواهید دوباره این تور راهنما را ببینید، روی این دکمه کلیک کنید.',
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
    // اضافه کردن کلاس dark mode
    if (document.documentElement.classList.contains('dark')) {
      this.tooltip.style.background = '#111827';
      this.tooltip.style.borderColor = '#374151';
      this.tooltip.style.color = '#f9fafb';
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

    this.tooltip.innerHTML = `
      <div class="mb-3">
        <h3 class="text-base font-semibold mb-1" style="color: ${textColor}">${step.title}</h3>
        <p class="text-sm leading-relaxed" style="color: ${textSecondary}">${step.description}</p>
        ${actionHtml}
      </div>
      <div class="flex items-center justify-between gap-2 pt-2" style="border-top-color: ${borderColor}">
        <div class="text-xs" style="color: ${textSecondary}">
          ${index + 1} از ${this.tourData.length}
        </div>
        <div class="flex items-center gap-2">
          ${index > 0 ? `
            <button onclick="window.onboardingTour.prevStep()" class="px-3 py-1.5 text-xs font-medium border rounded-lg hover:opacity-80 transition" style="border-color: ${borderColor}; color: ${textColor}">
              قبلی
            </button>
          ` : ''}
          ${step.action === 'navigate' && step.nextUrl ? `
            <button onclick="window.onboardingTour.navigateToNext('${step.nextUrl}')" class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
              برو به صفحه بعدی
            </button>
          ` : step.action === 'click' ? `
            <button onclick="window.onboardingTour.nextStep()" class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition opacity-50 cursor-not-allowed" disabled>
              روی المنت کلیک کنید
            </button>
          ` : `
            <button onclick="window.onboardingTour.nextStep()" class="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
              ${index === this.tourData.length - 1 ? 'پایان' : 'بعدی'}
            </button>
          `}
        </div>
      </div>
    `;

    this.tooltip.style.left = position.left + 'px';
    this.tooltip.style.top = position.top + 'px';

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

// شروع خودکار تور بعد از لود شدن صفحه
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.onboardingTour.init();
  });
} else {
  window.onboardingTour.init();
}

