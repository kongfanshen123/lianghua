const API_BASE = '/api';

const cache = {
    symbols: null,
    symbolsTimestamp: 0,
    qualitySummary: null,
    qualitySummaryTimestamp: 0,
    qualityDetails: null,
    qualityDetailsTimestamp: 0,
    coverage: null,
    coverageTimestamp: 0,
    qualityTrend: null,
    qualityTrendTimestamp: 0,
    latestResults: null,
    latestResultsTimestamp: 0,
    symbolPriceCounts: null,
    symbolPriceCountsTimestamp: 0,
    categorySummary: null,
    categorySummaryTimestamp: 0,
    systemStatus: null,
    systemStatusTimestamp: 0
};

const CACHE_DURATION = 60000;

function isCacheValid(timestamp) {
    return timestamp > 0 && (Date.now() - timestamp) < CACHE_DURATION;
}

function clearCache() {
    Object.keys(cache).forEach(key => {
        if (key.endsWith('Timestamp')) {
            cache[key] = 0;
        } else {
            cache[key] = null;
        }
    });
}

async function fetchAPI(endpoint, params = {}, method = 'GET') {
    let url = `${API_BASE}${endpoint}`;
    const paramArray = [];
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
            paramArray.push(`${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`);
        }
    });
    if (paramArray.length > 0) {
        url += '?' + paramArray.join('&');
    }
    
    const options = { method };
    if (method === 'POST') {
        options.headers = { 'Content-Type': 'application/json' };
    }
    
    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

async function getSymbols(status = null, search = null, category = null) {
    if (isCacheValid(cache.symbolsTimestamp) && !status && !search && !category) {
        return cache.symbols;
    }
    
    const params = {};
    if (status !== null && status !== '') params.status = status;
    if (search) params.search = search;
    if (category) params.category = category;
    const result = await fetchAPI('/symbols', params);
    
    if (!status && !search && !category) {
        cache.symbols = result;
        cache.symbolsTimestamp = Date.now();
    }
    return result;
}

async function getSymbolCategories() {
    return await fetchAPI('/symbols/categories');
}

async function getPrices(params = {}) {
    return await fetchAPI('/prices', params);
}

async function getPricesBySymbol(symbol) {
    return await fetchAPI(`/prices/symbol/${symbol}`);
}

async function getPricesCount() {
    return await fetchAPI('/prices/count');
}

async function getResults(tradeDate = null, category = null, page = 1, pageSize = 50) {
    const params = { page, page_size: pageSize };
    if (tradeDate) params.trade_date = tradeDate;
    if (category) params.category = category;
    return await fetchAPI('/results', params);
}

async function getLatestResults(category = null) {
    const params = {};
    if (category) params.category = category;
    
    if (isCacheValid(cache.latestResultsTimestamp) && !category) {
        return cache.latestResults;
    }
    
    const result = await fetchAPI('/results/latest', params);
    if (!category) {
        cache.latestResults = result;
        cache.latestResultsTimestamp = Date.now();
    }
    return result;
}

async function getCategorySummary() {
    if (isCacheValid(cache.categorySummaryTimestamp)) {
        return cache.categorySummary;
    }
    
    const result = await fetchAPI('/results/category-summary');
    cache.categorySummary = result;
    cache.categorySummaryTimestamp = Date.now();
    return result;
}

async function getQualitySummary() {
    if (isCacheValid(cache.qualitySummaryTimestamp)) {
        return cache.qualitySummary;
    }
    
    const result = await fetchAPI('/quality/summary');
    cache.qualitySummary = result;
    cache.qualitySummaryTimestamp = Date.now();
    return result;
}

async function getQualityDetails(issueType = null) {
    const params = {};
    if (issueType) params.issue_type = issueType;
    
    if (isCacheValid(cache.qualityDetailsTimestamp) && !issueType) {
        return cache.qualityDetails;
    }
    
    const result = await fetchAPI('/quality/details', params);
    if (!issueType) {
        cache.qualityDetails = result;
        cache.qualityDetailsTimestamp = Date.now();
    }
    return result;
}

async function getCoverage() {
    if (isCacheValid(cache.coverageTimestamp)) {
        return cache.coverage;
    }
    
    const result = await fetchAPI('/quality/coverage');
    cache.coverage = result;
    cache.coverageTimestamp = Date.now();
    return result;
}

async function getQualityTrend(days = 30) {
    const cacheKey = `qualityTrend_${days}`;
    if (isCacheValid(cache[`${cacheKey}Timestamp`])) {
        return cache[cacheKey];
    }
    
    const result = await fetchAPI('/quality/trend', { days });
    cache[cacheKey] = result;
    cache[`${cacheKey}Timestamp`] = Date.now();
    return result;
}

async function getSymbolPriceCounts() {
    if (isCacheValid(cache.symbolPriceCountsTimestamp)) {
        return cache.symbolPriceCounts;
    }
    
    try {
        const result = await fetchAPI('/prices/counts');
        cache.symbolPriceCounts = result;
        cache.symbolPriceCountsTimestamp = Date.now();
        return result;
    } catch (e) {
        return { data: {} };
    }
}

async function getSystemStatus() {
    if (isCacheValid(cache.systemStatusTimestamp)) {
        return cache.systemStatus;
    }
    
    const result = await fetchAPI('/system/status');
    cache.systemStatus = result;
    cache.systemStatusTimestamp = Date.now();
    return result;
}

async function triggerFetch(symbol = null, days = 60) {
    const params = {};
    if (symbol) params.symbol = symbol;
    if (days) params.days = days;
    return await fetchAPI('/tasks/fetch', params, 'POST');
}

async function triggerCalculate() {
    return await fetchAPI('/tasks/calculate', {}, 'POST');
}

async function triggerRepair(symbol = null) {
    const params = {};
    if (symbol) params.symbol = symbol;
    return await fetchAPI('/tasks/repair', params, 'POST');
}

async function triggerFullPipeline() {
    return await fetchAPI('/tasks/full', {}, 'POST');
}