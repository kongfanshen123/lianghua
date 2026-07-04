let currentPricePage = 1;
let isLoading = false;
let currentCategory = 'market';

document.addEventListener('DOMContentLoaded', async () => {
    initCharts();
    initNavigation();
    updateCurrentDate();
    initDatePickers();
    await loadLatestResultsForMomentum();
    await loadSystemStatus();
    
    const searchInput = document.getElementById('globalSearch');
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') handleGlobalSearch();
    });
    searchInput.addEventListener('input', debounce(handleSearchInput, 300));
    searchInput.addEventListener('focus', showSearchSuggestions);
    
    document.addEventListener('click', function(e) {
        const searchWrapper = document.querySelector('.search-wrapper');
        if (!searchWrapper.contains(e.target)) {
            hideSearchSuggestions();
        }
    });
    
    document.getElementById('symbolCategory').addEventListener('change', loadSymbols);
    document.getElementById('symbolStatus').addEventListener('change', loadSymbols);
});

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', function() {
            const target = this.dataset.target;
            switchPage(target);
        });
    });
    
    document.querySelectorAll('.header-tab').forEach(btn => {
        btn.addEventListener('click', function() {
            const target = this.dataset.subtab;
            switchSubPage(target);
        });
    });
    
    document.querySelectorAll('.category-tab').forEach(btn => {
        btn.addEventListener('click', function() {
            const category = this.dataset.category;
            switchCategory(category);
        });
    });
}

function switchPage(pageId) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.nav-item[data-target="${pageId}"]`).classList.add('active');
    
    document.querySelectorAll('.page-tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
    
    if (pageId === 'tabQuality') {
        loadQualitySummary();
        loadQualityDetails();
        loadCoverage();
        loadQualityTrend();
        updateIssueDistributionChart();
    } else if (pageId === 'tabData') {
        loadSymbols();
        loadPriceSymbolOptions(true);
    }
}

function switchSubPage(subPageId) {
    document.querySelectorAll('.header-tab').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.header-tab[data-subtab="${subPageId}"]`).classList.add('active');
    
    document.querySelectorAll('.sub-page').forEach(page => page.classList.add('hidden'));
    document.getElementById(subPageId).classList.remove('hidden');
    
    if (subPageId === 'dataPrices') {
        loadPriceSymbolOptions();
    }
}

let priceSymbolChangeHandlerAdded = false;

document.addEventListener('DOMContentLoaded', () => {
    const priceSymbolSelect = document.getElementById('priceSymbol');
    if (priceSymbolSelect && !priceSymbolChangeHandlerAdded) {
        priceSymbolSelect.addEventListener('change', loadPrices);
        priceSymbolChangeHandlerAdded = true;
    }
});

function switchCategory(category) {
    currentCategory = category;
    document.querySelectorAll('.category-tab').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.category-tab[data-category="${category}"]`).classList.add('active');
    loadLatestResultsForMomentum();
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function updateCurrentDate() {
    const now = new Date();
    const dateStr = now.toLocaleDateString('zh-CN', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        weekday: 'long'
    });
    document.getElementById('currentDate').textContent = dateStr;
}

function initDatePickers() {
    const pickers = document.querySelectorAll('.date-picker');
    pickers.forEach(picker => {
        picker.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDatePicker(picker);
        });
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.date-calendar.show').forEach(cal => {
            cal.classList.remove('show');
        });
        document.querySelectorAll('.date-picker.active').forEach(picker => {
            picker.classList.remove('active');
        });
    });
}

function toggleDatePicker(picker) {
    const wrapper = picker.parentElement;
    let calendar = wrapper.querySelector('.date-calendar');
    
    document.querySelectorAll('.date-calendar.show').forEach(cal => {
        cal.classList.remove('show');
    });
    document.querySelectorAll('.date-picker.active').forEach(p => {
        p.classList.remove('active');
    });

    if (!calendar) {
        calendar = createDateCalendar();
        wrapper.appendChild(calendar);
    }

    picker.classList.add('active');
    calendar.classList.add('show');
    
    const targetId = picker.dataset.target;
    const selectedDate = document.getElementById(targetId).value;
    renderCalendar(calendar, selectedDate);

    calendar.querySelectorAll('.date-calendar-day').forEach(day => {
        day.addEventListener('click', (e) => {
            e.stopPropagation();
            const date = day.dataset.date;
            if (date) {
                selectDate(calendar, picker, date);
            }
        });
    });

    calendar.querySelector('.date-calendar-nav.prev').addEventListener('click', (e) => {
        e.stopPropagation();
        navigateMonth(calendar, -1);
    });

    calendar.querySelector('.date-calendar-nav.next').addEventListener('click', (e) => {
        e.stopPropagation();
        navigateMonth(calendar, 1);
    });

    calendar.querySelector('.date-calendar-btn.today').addEventListener('click', (e) => {
        e.stopPropagation();
        const today = new Date().toISOString().split('T')[0];
        selectDate(calendar, picker, today);
    });

    calendar.querySelector('.date-calendar-btn.clear').addEventListener('click', (e) => {
        e.stopPropagation();
        clearDate(calendar, picker);
    });
}

function createDateCalendar() {
    const calendar = document.createElement('div');
    calendar.className = 'date-calendar';
    calendar.innerHTML = `
        <div class="date-calendar-header">
            <button class="date-calendar-nav prev"><i class="fa fa-chevron-left"></i></button>
            <span class="date-calendar-title"></span>
            <button class="date-calendar-nav next"><i class="fa fa-chevron-right"></i></button>
        </div>
        <div class="date-calendar-weekdays">
            <span class="date-calendar-weekday">日</span>
            <span class="date-calendar-weekday">一</span>
            <span class="date-calendar-weekday">二</span>
            <span class="date-calendar-weekday">三</span>
            <span class="date-calendar-weekday">四</span>
            <span class="date-calendar-weekday">五</span>
            <span class="date-calendar-weekday">六</span>
        </div>
        <div class="date-calendar-days"></div>
        <div class="date-calendar-footer">
            <button class="date-calendar-btn clear">清除</button>
            <button class="date-calendar-btn primary today">今天</button>
        </div>
    `;
    return calendar;
}

function renderCalendar(calendar, selectedDate) {
    const current = calendar.dataset.currentDate ? new Date(calendar.dataset.currentDate) : new Date();
    const year = current.getFullYear();
    const month = current.getMonth();

    calendar.querySelector('.date-calendar-title').textContent = `${year}年${month + 1}月`;

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysContainer = calendar.querySelector('.date-calendar-days');
    
    let html = '';

    const startPadding = firstDay.getDay();
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    for (let i = startPadding - 1; i >= 0; i--) {
        const day = prevMonthLastDay - i;
        const date = new Date(year, month - 1, day);
        html += `<button class="date-calendar-day other-month" data-date="${date.toISOString().split('T')[0]}">${day}</button>`;
    }

    const today = new Date().toISOString().split('T')[0];
    for (let day = 1; day <= lastDay.getDate(); day++) {
        const date = new Date(year, month, day).toISOString().split('T')[0];
        let classes = 'date-calendar-day';
        if (date === today) classes += ' today';
        if (date === selectedDate) classes += ' selected';
        html += `<button class="${classes}" data-date="${date}">${day}</button>`;
    }

    const remainingDays = 42 - (startPadding + lastDay.getDate());
    for (let day = 1; day <= remainingDays; day++) {
        const date = new Date(year, month + 1, day);
        html += `<button class="date-calendar-day other-month" data-date="${date.toISOString().split('T')[0]}">${day}</button>`;
    }

    daysContainer.innerHTML = html;
}

function navigateMonth(calendar, direction) {
    const current = calendar.dataset.currentDate ? new Date(calendar.dataset.currentDate) : new Date();
    current.setMonth(current.getMonth() + direction);
    calendar.dataset.currentDate = current.toISOString();
    
    const targetId = calendar.parentElement.querySelector('.date-picker').dataset.target;
    const selectedDate = document.getElementById(targetId).value;
    renderCalendar(calendar, selectedDate);
}

function selectDate(calendar, picker, date) {
    const targetId = picker.dataset.target;
    const hiddenInput = document.getElementById(targetId);
    hiddenInput.value = date;

    const dateObj = new Date(date);
    const displayDate = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}-${String(dateObj.getDate()).padStart(2, '0')}`;
    picker.querySelector('.date-picker-value').textContent = displayDate;

    calendar.classList.remove('show');
    picker.classList.remove('active');
}

function clearDate(calendar, picker) {
    const targetId = picker.dataset.target;
    const hiddenInput = document.getElementById(targetId);
    hiddenInput.value = '';
    picker.querySelector('.date-picker-value').textContent = '选择日期';

    calendar.classList.remove('show');
    picker.classList.remove('active');
}

async function loadSystemStatus() {
    try {
        const status = await getSystemStatus();
        const statusEl = document.getElementById('systemStatus');
        const indicator = statusEl.querySelector('.status-indicator');
        const text = statusEl.querySelector('span:last-child');
        
        let statusClass = 'offline';
        let statusText = '系统离线';
        
        if (status.price_status === 'up_to_date' && status.result_status === 'up_to_date') {
            statusClass = '';
            statusText = '系统正常';
        } else if (status.price_status === 'delayed' || status.result_status === 'delayed') {
            statusClass = 'delayed';
            statusText = '数据延迟';
        }
        
        indicator.className = `status-indicator ${statusClass}`;
        text.textContent = statusText;
    } catch (error) {
        console.error('Failed to load system status:', error);
    }
}

async function refreshAllData() {
    clearCache();
    await loadLatestResultsForMomentum();
    loadQualitySummary();
    loadQualityDetails();
    loadCoverage();
    loadQualityTrend();
    loadSymbols();
    await loadSystemStatus();
}

function handleGlobalSearch() {
    const searchText = document.getElementById('globalSearch').value.trim();
    if (!searchText) return;
    
    switchSubPage('dataSymbols');
    switchPage('tabData');
    hideSearchSuggestions();
    
    const categorySelect = document.getElementById('symbolCategory');
    const statusSelect = document.getElementById('symbolStatus');
    categorySelect.value = '';
    statusSelect.value = '';
    
    loadSymbolsWithSearch(searchText);
}

function handleSearchInput() {
    const searchText = document.getElementById('globalSearch').value.trim();
    if (searchText.length >= 1) {
        showSearchSuggestions(searchText);
    } else {
        hideSearchSuggestions();
    }
}

async function showSearchSuggestions(searchText = '') {
    const suggestionsEl = document.getElementById('searchSuggestions');
    
    if (!searchText) {
        searchText = document.getElementById('globalSearch').value.trim();
    }
    
    if (!searchText) {
        suggestionsEl.innerHTML = '';
        suggestionsEl.classList.remove('show');
        return;
    }
    
    try {
        const result = await getSymbols(null, searchText, null);
        const items = result.data || [];
        
        if (items.length === 0) {
            suggestionsEl.innerHTML = '<div class="search-suggestion-item" style="color: var(--text-muted);">未找到匹配的标的</div>';
            suggestionsEl.classList.add('show');
            return;
        }
        
        const categoryMap = {
            'market': '大盘',
            'industry': '行业'
        };
        
        const html = items.slice(0, 8).map(item => `
            <div class="search-suggestion-item" onclick="selectSearchResult('${item.symbol}')">
                <span class="suggestion-symbol">${item.symbol}</span>
                <span class="suggestion-name">${item.name}</span>
                <span class="suggestion-category">${categoryMap[item.category] || item.category}</span>
            </div>
        `).join('');
        
        suggestionsEl.innerHTML = html;
        suggestionsEl.classList.add('show');
    } catch (error) {
        console.error('Failed to load search suggestions:', error);
        suggestionsEl.classList.remove('show');
    }
}

function hideSearchSuggestions() {
    document.getElementById('searchSuggestions').classList.remove('show');
}

function selectSearchResult(symbol) {
    document.getElementById('globalSearch').value = symbol;
    hideSearchSuggestions();
    viewPrices(symbol);
}

async function loadSymbolsWithSearch(searchText) {
    if (isLoading) return;
    isLoading = true;
    
    const tbody = document.getElementById('symbolTable').querySelector('tbody');
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#6b6b80;"><i class="fa fa-spinner fa-spin"></i> 加载中...</td></tr>';
    
    try {
        const [symbolsResult, countsResult] = await Promise.all([
            getSymbols(null, searchText, null),
            getSymbolPriceCounts()
        ]);
        
        const countsMap = countsResult.data || {};
        
        const categoryMap = {
            'market': '大盘指标',
            'industry': '行业指标'
        };
        
        const rows = symbolsResult.data.map(item => {
            const priceCount = countsMap[item.symbol] || 0;
            const statusText = item.status === 1 
                ? '<span class="badge active">启用</span>' 
                : '<span class="badge disabled">禁用</span>';
            const categoryText = categoryMap[item.category] || item.category;
            
            return `
                <tr>
                    <td>${item.symbol}</td>
                    <td>${item.name}</td>
                    <td>${categoryText}</td>
                    <td>${item.market}</td>
                    <td>${item.data_source}</td>
                    <td>${statusText}</td>
                    <td>${priceCount}</td>
                    <td><button class="btn btn-sm btn-primary" onclick="viewPrices('${item.symbol}')">查看</button></td>
                </tr>
            `;
        });
        
        tbody.innerHTML = rows.join('');
    } catch (error) {
        console.error('Failed to load symbols:', error);
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#f87171;">加载标的列表失败</td></tr>';
    } finally {
        isLoading = false;
    }
}

async function loadSymbols() {
    if (isLoading) return;
    isLoading = true;
    
    const status = document.getElementById('symbolStatus').value;
    const category = document.getElementById('symbolCategory').value;
    
    const tbody = document.getElementById('symbolTable').querySelector('tbody');
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#6b6b80;"><i class="fa fa-spinner fa-spin"></i> 加载中...</td></tr>';
    
    try {
        const [symbolsResult, countsResult] = await Promise.all([
            getSymbols(status, null, category),
            getSymbolPriceCounts()
        ]);
        
        const countsMap = countsResult.data || {};
        
        const categoryMap = {
            'market': '大盘指标',
            'industry': '行业指标'
        };
        
        const rows = symbolsResult.data.map(item => {
            const priceCount = countsMap[item.symbol] || 0;
            const statusText = item.status === 1 
                ? '<span class="badge active">启用</span>' 
                : '<span class="badge disabled">禁用</span>';
            const categoryText = categoryMap[item.category] || item.category;
            
            return `
                <tr>
                    <td>${item.symbol}</td>
                    <td>${item.name}</td>
                    <td>${categoryText}</td>
                    <td>${item.market}</td>
                    <td>${item.data_source}</td>
                    <td>${statusText}</td>
                    <td>${priceCount}</td>
                    <td><button class="btn btn-sm btn-primary" onclick="viewPrices('${item.symbol}')">查看</button></td>
                </tr>
            `;
        });
        
        tbody.innerHTML = rows.join('');
    } catch (error) {
        console.error('Failed to load symbols:', error);
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#f87171;">加载标的列表失败</td></tr>';
    } finally {
        isLoading = false;
    }
}

async function loadPriceSymbolOptions(selectDefault = false) {
    try {
        const result = await getSymbols();
        const select = document.getElementById('priceSymbol');
        select.innerHTML = '<option value="">全部标的</option>';
        
        const sortedData = [...result.data].sort((a, b) => {
            if (a.category === 'market' && b.category !== 'market') return -1;
            if (a.category !== 'market' && b.category === 'market') return 1;
            return a.symbol.localeCompare(b.symbol);
        });
        
        sortedData.forEach(item => {
            const option = document.createElement('option');
            option.value = item.symbol;
            option.textContent = `${item.symbol} - ${item.name}`;
            select.appendChild(option);
        });
        
        if (selectDefault) {
            select.value = '000905';
            loadPrices();
        }
    } catch (error) {
        console.error('Failed to load symbol options:', error);
    }
}

async function loadPrices(page = 1) {
    currentPricePage = page;
    const symbol = document.getElementById('priceSymbol').value;
    
    const tbody = document.getElementById('priceTable').querySelector('tbody');
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#6b6b80;"><i class="fa fa-spinner fa-spin"></i> 加载中...</td></tr>';
    
    try {
        const tableParams = { page, page_size: 50 };
        if (symbol) tableParams.symbol = symbol;
        
        const [tableResult, klineResult] = await Promise.all([
            getPrices(tableParams),
            getPrices({ symbol, page: 1, page_size: 1000 })
        ]);
        
        if (typeof updateKlineChart === 'function') {
            updateKlineChart(klineResult.data || []);
        }
        
        const rows = tableResult.data.map(item => `
            <tr>
                <td>${item.trade_date}</td>
                <td>${item.symbol || item.name || ''}</td>
                <td>${item.open_price}</td>
                <td>${item.high_price}</td>
                <td>${item.low_price}</td>
                <td>${item.close_price}</td>
                <td>${formatNumber(item.volume)}</td>
                <td>${formatNumber(item.amount)}</td>
            </tr>
        `);
        
        tbody.innerHTML = rows.join('');
        renderPagination(tableResult.total, page, 50, 'pricePagination', '', loadPrices);
    } catch (error) {
        console.error('Failed to load prices:', error);
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#f87171;">加载价格数据失败</td></tr>';
    }
}

function viewPrices(symbol) {
    document.getElementById('priceSymbol').value = symbol;
    switchSubPage('dataPrices');
    loadPrices();
}

async function loadQualitySummary() {
    try {
        const result = await getQualitySummary();
        
        animateValue('statActiveSymbols', result.active_symbols);
        animateValue('statTotalRecords', formatNumber(result.total_price_records));
        
        const daysDelay = document.getElementById('statDaysDelay');
        daysDelay.textContent = result.days_since_latest;
        if (result.days_since_latest > 5) {
            daysDelay.style.color = '#f87171';
        } else {
            daysDelay.style.color = '#4ade80';
        }
        
        const issues = result.symbols_without_data + result.duplicate_records + 
                      result.zero_volume_non_suspended + result.negative_price + result.price_jumps;
        animateValue('statIssues', issues);
        
        animateValue('issueNoDataCount', result.symbols_without_data);
        animateValue('issueNegativePriceCount', result.negative_price);
        animateValue('issueZeroVolumeCount', result.zero_volume_non_suspended);
        animateValue('issueDuplicateCount', result.duplicate_records);
        animateValue('issuePriceJumpCount', result.price_jumps || 0);
    } catch (error) {
        console.error('Failed to load quality summary:', error);
    }
}

async function loadQualityDetails() {
    try {
        const issueType = document.getElementById('issueType').value;
        const result = await getQualityDetails(issueType);
        const tbody = document.getElementById('issueTable').querySelector('tbody');
        
        if (result.issues.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:40px; color:#6b6b80;">暂无异常数据</td></tr>';
            return;
        }
        
        const typeMap = {
            no_data: { label: '无数据', color: 'yellow' },
            negative_price: { label: '价格异常', color: 'red' },
            zero_volume: { label: '零成交量', color: 'yellow' },
            duplicate: { label: '重复数据', color: 'red' },
            price_jump: { label: '价格跳变', color: 'red' }
        };
        
        const rows = result.issues.map(item => {
            const typeInfo = typeMap[item.type] || { label: item.type, color: 'gray' };
            let badgeColor = 'background: rgba(107,107,128,0.2); color: #6b6b80;';
            if (typeInfo.color === 'red') badgeColor = 'background: rgba(248,113,113,0.15); color: #f87171;';
            if (typeInfo.color === 'yellow') badgeColor = 'background: rgba(251,191,36,0.15); color: #fbbf24;';
            
            return `
                <tr>
                    <td><span class="badge" style="${badgeColor}">${typeInfo.label}</span></td>
                    <td>${item.symbol} - ${item.name}</td>
                    <td>${item.trade_date || '-'}</td>
                    <td>${item.description}</td>
                    <td>${Number.isFinite(item.change_pct) ? item.change_pct : (item.close_price != null ? item.close_price : (item.count != null ? item.count : '-'))}</td>
                    <td><button class="btn btn-sm btn-primary" onclick="viewPrices('${item.symbol}')">查看</button></td>
                </tr>
            `;
        });
        
        tbody.innerHTML = rows.join('');
    } catch (error) {
        console.error('Failed to load quality details:', error);
    }
}

async function loadCoverage() {
    try {
        const result = await getCoverage();
        const tbody = document.getElementById('coverageTable').querySelector('tbody');
        
        const categoryMap = {
            'market': '大盘指标',
            'industry': '行业指标'
        };
        
        const rows = result.data.map(item => {
            let statusBadge = '<span class="badge" style="background: rgba(74,222,128,0.15); color: #4ade80;">良好</span>';
            if (item.status === 'warning') {
                statusBadge = '<span class="badge" style="background: rgba(251,191,36,0.15); color: #fbbf24;">警告</span>';
            } else if (item.status !== 'good') {
                statusBadge = '<span class="badge" style="background: rgba(248,113,113,0.15); color: #f87171;">严重</span>';
            }
            
            const categoryText = categoryMap[item.category] || item.category;
            
            return `
                <tr>
                    <td>${item.symbol}</td>
                    <td>${categoryText}</td>
                    <td>${item.record_count}</td>
                    <td>${item.first_date}</td>
                    <td>${item.last_date}</td>
                    <td>${item.coverage}%</td>
                    <td>${statusBadge}</td>
                    <td><button class="btn btn-sm btn-primary" onclick="viewPrices('${item.symbol}')">查看</button></td>
                </tr>
            `;
        });
        
        tbody.innerHTML = rows.join('');
    } catch (error) {
        console.error('Failed to load coverage:', error);
    }
}

async function loadQualityTrend() {
    try {
        const result = await getQualityTrend(30);
        updateQualityTrendChart(result.data);
        updateIssueDistributionChart();
    } catch (error) {
        console.error('Failed to load quality trend:', error);
    }
}

async function updateIssueDistributionChart() {
    try {
        const result = await getQualityDetails();
        const distribution = {};
        
        result.issues.forEach(item => {
            distribution[item.type] = (distribution[item.type] || 0) + 1;
        });
        
        const typeLabels = {
            no_data: '无数据',
            negative_price: '价格异常',
            zero_volume: '零成交量',
            duplicate: '重复数据',
            price_jump: '价格跳变'
        };
        
        const colors = {
            no_data: '#fbbf24',
            negative_price: '#f87171',
            zero_volume: '#fbbf24',
            duplicate: '#f87171',
            price_jump: '#f87171'
        };
        
        const data = Object.entries(distribution).map(([key, value]) => ({
            name: typeLabels[key] || key,
            value: value,
            itemStyle: { color: colors[key] || '#6b6b80' }
        }));
        
        renderIssueDistributionChart(data);
    } catch (error) {
        console.error('Failed to update issue distribution chart:', error);
    }
}

async function loadLatestResultsForMomentum() {
    try {
        const result = await getLatestResults(currentCategory === 'all' ? null : currentCategory);
        
        if (result.data && result.data.length > 0) {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
            document.getElementById('momentumTimestamp').textContent = `数据更新时间: ${timeStr}`;
        }
        
        updateMomentumCharts(result.data);
        
        const tbody = document.getElementById('momentumTable').querySelector('tbody');
        
        const categoryMap = {
            'market': '大盘指标',
            'industry': '行业指标'
        };
        
        const rows = result.data.map(item => {
            const rankingChange = item.ranking_change;
            let changeIcon = '';
            if (rankingChange > 0) changeIcon = '<span class="badge up">↑' + rankingChange + '</span>';
            else if (rankingChange < 0) changeIcon = '<span class="badge down">↓' + Math.abs(rankingChange) + '</span>';
            else changeIcon = '<span class="badge same">→</span>';
            
            const trendColor = getTrendColor(item.trend_strength);
            const categoryText = categoryMap[item.category] || item.category;
            
            const momentumVal = parseFloat(item.momentum_20d) || 0;
            const momentumColor = momentumVal >= 0 ? 'color: var(--accent-green); font-weight: 600;' : 'color: var(--accent-red); font-weight: 600;';
            
            return `
                <tr onclick="openKlineModal('${item.symbol}', '${item.name}')" style="cursor: pointer;">
                    <td>${item.ranking}</td>
                    <td>${item.symbol} - ${item.name}</td>
                    <td>${categoryText}</td>
                    <td style="${momentumColor}">${formatMomentum(item.momentum_20d)}</td>
                    <td>${item.volume_confirmed ? '✓' : '✗'}</td>
                    <td>${item.volume_change_pct}%</td>
                    <td><span style="color: ${trendColor}">${item.trend_strength}</span></td>
                    <td>${changeIcon}</td>
                </tr>
            `;
        });
        
        tbody.innerHTML = rows.join('');
    } catch (error) {
        console.error('Failed to load momentum results:', error);
    }
}

function renderPagination(total, page, pageSize, topId, bottomId, callback) {
    const pages = Math.ceil(total / pageSize);
    if (pages <= 1) {
        document.getElementById(topId).innerHTML = '';
        if (bottomId) document.getElementById(bottomId).innerHTML = '';
        return;
    }
    
    let html = '';
    
    if (page > 1) {
        html += `<button onclick="${callback.name}(${page - 1})"><i class="fa fa-chevron-left"></i></button>`;
    }
    
    for (let i = Math.max(1, page - 2); i <= Math.min(pages, page + 2); i++) {
        const active = i === page ? 'active' : '';
        html += `<button class="${active}" onclick="${callback.name}(${i})">${i}</button>`;
    }
    
    if (page < pages) {
        html += `<button onclick="${callback.name}(${page + 1})"><i class="fa fa-chevron-right"></i></button>`;
    }
    
    document.getElementById(topId).innerHTML = html;
    if (bottomId) document.getElementById(bottomId).innerHTML = html;
}

function formatNumber(num) {
    if (num === null || num === undefined) return '-';
    if (num >= 100000000) return (num / 100000000).toFixed(2) + '亿';
    if (num >= 10000) return (num / 10000).toFixed(2) + '万';
    return num.toString();
}

function formatMomentum(value) {
    if (value === null || value === undefined) return '-';
    const num = parseFloat(value);
    if (isNaN(num)) return '-';
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
}

function getTrendColor(trend) {
    const colors = {
        '极强上涨': '#4ade80',
        '较强上涨': '#73d13d',
        '微弱上涨': '#a3d959',
        '微弱下跌': '#ff7875',
        '较强下跌': '#f87171',
        '极强下跌': '#ef4444'
    };
    return colors[trend] || '#6b6b80';
}

function animateValue(id, endValue) {
    const element = document.getElementById(id);
    if (!element) return;
    
    const startValue = parseInt(element.textContent.replace(/[^\d]/g, '')) || 0;
    const duration = 800;
    const startTime = Date.now();
    
    function update() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        
        const targetNum = parseInt(endValue.toString().replace(/[^\d-]/g, '')) || 0;
        const currentValue = Math.floor(startValue + (targetNum - startValue) * easeOutQuart);
        
        if (typeof endValue === 'string' && endValue.includes('%')) {
            element.textContent = (currentValue / 100).toFixed(2) + '%';
        } else if (typeof endValue === 'string' && endValue.includes('万')) {
            element.textContent = (currentValue / 10000).toFixed(2) + '万';
        } else if (typeof endValue === 'string' && endValue.includes('亿')) {
            element.textContent = (currentValue / 100000000).toFixed(2) + '亿';
        } else {
            element.textContent = currentValue;
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            element.textContent = endValue;
        }
    }
    
    requestAnimationFrame(update);
}

function openUpdateModal() {
    document.getElementById('updateModal').classList.add('show');
    document.getElementById('updateResult').classList.remove('show');
}

function closeUpdateModal() {
    document.getElementById('updateModal').classList.remove('show');
}

function openRepairModal() {
    document.getElementById('repairModal').classList.add('show');
    document.getElementById('repairResult').classList.remove('show');
}

function closeRepairModal() {
    document.getElementById('repairModal').classList.remove('show');
}

function openKlineModal(symbol, name) {
    document.getElementById('klineModalTitle').textContent = `${symbol} - ${name} K线图`;
    document.getElementById('klineModal').classList.add('show');
    
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
    const startDate = oneYearAgo.toISOString().split('T')[0];
    const endDate = new Date().toISOString().split('T')[0];
    
    loadKlineForModal(symbol, startDate, endDate);
}

function closeKlineModal() {
    document.getElementById('klineModal').classList.remove('show');
}

async function loadKlineForModal(symbol, startDate, endDate) {
    try {
        const result = await getPrices({ symbol, start_date: startDate, end_date: endDate, page: 1, page_size: 1000 });
        updateModalKlineChart(result.data || []);
    } catch (error) {
        console.error('Failed to load K-line data:', error);
    }
}

async function executeTask(taskType) {
    const resultEl = document.getElementById(taskType === 'repair' ? 'repairResult' : 'updateResult');
    resultEl.className = 'modal-result loading show';
    resultEl.innerHTML = '<i class="fa fa-spinner fa-spin"></i> 正在执行，请稍候...';
    
    try {
        let result;
        switch (taskType) {
            case 'fetch':
                result = await triggerFetch();
                break;
            case 'calculate':
                result = await triggerCalculate();
                break;
            case 'full':
                result = await triggerFullPipeline();
                break;
            case 'repair':
                result = await triggerRepair();
                break;
        }
        
        if (result.status === 'success') {
            resultEl.className = 'modal-result success show';
            resultEl.innerHTML = '<i class="fa fa-check-circle"></i> 执行成功！';
            setTimeout(() => {
                if (taskType === 'repair') {
                    closeRepairModal();
                } else {
                    closeUpdateModal();
                }
                refreshAllData();
            }, 1500);
        } else {
            resultEl.className = 'modal-result error show';
            resultEl.innerHTML = `<i class="fa fa-exclamation-circle"></i> 执行失败：${result.message.substring(0, 200)}`;
        }
    } catch (error) {
        resultEl.className = 'modal-result error show';
        resultEl.innerHTML = `<i class="fa fa-exclamation-circle"></i> 执行失败：${error.message}`;
    }
}