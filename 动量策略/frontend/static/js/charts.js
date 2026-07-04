let momentumBarChart = null;
let qualityTrendChart = null;
let klineChart = null;
let issueDistributionChart = null;
let chartsInitialized = false;

const DARK_COLORS = {
    bg: '#16162a',
    bgLight: '#252540',
    border: '#2d2d4a',
    text: '#ffffff',
    textSecondary: '#a0a0b8',
    textMuted: '#6b6b80',
    blue: '#4a9eff',
    green: '#4ade80',
    red: '#f87171',
    yellow: '#fbbf24',
    purple: '#a78bfa',
    cyan: '#22d3ee'
};

function initCharts() {
    if (chartsInitialized) return;
    
    const containers = [
        { id: 'momentumBarChart', chart: 'momentumBarChart' },
        { id: 'qualityTrendChart', chart: 'qualityTrendChart' },
        { id: 'klineChart', chart: 'klineChart' },
        { id: 'issueDistributionChart', chart: 'issueDistributionChart' }
    ];
    
    containers.forEach(({ id }) => {
        const container = document.getElementById(id);
        if (container) {
            const chart = echarts.init(container);
            if (id === 'momentumBarChart') momentumBarChart = chart;
            else if (id === 'qualityTrendChart') qualityTrendChart = chart;
            else if (id === 'klineChart') klineChart = chart;
            else if (id === 'issueDistributionChart') issueDistributionChart = chart;
        }
    });
    
    chartsInitialized = true;
}

function ensureChartInitialized(chartType) {
    if (!chartsInitialized) initCharts();
    
    const chartMap = {
        bar: { id: 'momentumBarChart', ref: 'momentumBarChart' },
        trend: { id: 'qualityTrendChart', ref: 'qualityTrendChart' },
        kline: { id: 'klineChart', ref: 'klineChart' },
        issue: { id: 'issueDistributionChart', ref: 'issueDistributionChart' }
    };
    
    const config = chartMap[chartType];
    if (config) {
        const container = document.getElementById(config.id);
        if (container && !window[config.ref]) {
            window[config.ref] = echarts.init(container);
        }
    }
}

function debounceChartUpdate(func) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), 100);
    };
}

const debouncedUpdateMomentumBar = debounceChartUpdate(renderMomentumBarChart);
const debouncedUpdateQualityTrend = debounceChartUpdate(renderQualityTrendChart);
const debouncedUpdateIssueDistribution = debounceChartUpdate(renderIssueDistributionChart);

function renderMomentumBarChart(data) {
    ensureChartInitialized('bar');
    if (!momentumBarChart) return;
    
    const sortedData = [...data].sort((a, b) => b.momentum_20d - a.momentum_20d);
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: DARK_COLORS.bgLight,
            borderColor: DARK_COLORS.border,
            borderWidth: 1,
            textStyle: { color: DARK_COLORS.text },
            formatter: (params) => {
                const item = params[0];
                const dataIndex = item.dataIndex;
                const symbolData = sortedData[dataIndex];
                return `<div style="font-weight:500">${item.name}</div>
                        <div>20日动量: <strong>${(parseFloat(item.value) || 0).toFixed(2)}%</strong></div>
                        <div>趋势: ${symbolData.trend_strength || '-'}</div>`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '10%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: sortedData.map(item => item.name),
            axisLine: { lineStyle: { color: DARK_COLORS.border } },
            axisTick: { show: false },
            axisLabel: {
                rotate: 45,
                fontSize: 11,
                color: DARK_COLORS.textMuted
            }
        },
        yAxis: {
            type: 'value',
            name: '20日动量(%)',
            nameTextStyle: { color: DARK_COLORS.textMuted, fontSize: 12 },
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { 
                color: DARK_COLORS.textMuted, 
                fontSize: 11,
                formatter: (value) => (parseFloat(value) || 0).toFixed(1) + '%'
            },
            splitLine: { lineStyle: { color: DARK_COLORS.border, type: 'dashed' } }
        },
        series: [{
            type: 'bar',
            barWidth: '60%',
            data: sortedData.map(item => {
                const value = parseFloat(item.momentum_20d) || 0;
                return {
                    value: value,
                    itemStyle: {
                        color: value >= 0 
                            ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: DARK_COLORS.green },
                                { offset: 1, color: '#3ade70' }
                            ])
                            : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: DARK_COLORS.red },
                                { offset: 1, color: '#ef4444' }
                            ]),
                        borderRadius: [4, 4, 0, 0]
                    }
                };
            }),
            label: {
                show: true,
                position: 'top',
                fontSize: 11,
                fontWeight: 600,
                formatter: (params) => {
                    const value = parseFloat(params.value) || 0;
                    return value >= 0 ? '+' + value.toFixed(2) + '%' : value.toFixed(2) + '%';
                },
                color: function(params) {
                    const value = parseFloat(params.value) || 0;
                    return value >= 0 ? DARK_COLORS.green : DARK_COLORS.red;
                }
            }
        }]
    };
    
    momentumBarChart.setOption(option);
}

function renderQualityTrendChart(data) {
    ensureChartInitialized('trend');
    if (!qualityTrendChart) return;
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: DARK_COLORS.bgLight,
            borderColor: DARK_COLORS.border,
            borderWidth: 1,
            textStyle: { color: DARK_COLORS.text }
        },
        legend: {
            data: ['标的数', '记录数'],
            top: '0%',
            textStyle: { color: DARK_COLORS.textSecondary, fontSize: 12 },
            itemGap: 24,
            itemWidth: 16,
            itemHeight: 8,
            itemStyle: { borderRadius: 2 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            top: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: data.map(item => item.date),
            axisLine: { lineStyle: { color: DARK_COLORS.border } },
            axisTick: { show: false },
            axisLabel: {
                rotate: 45,
                fontSize: 10,
                color: DARK_COLORS.textMuted
            }
        },
        yAxis: {
            type: 'value',
            axisLine: { show: false },
            axisTick: { show: false },
            axisLabel: { color: DARK_COLORS.textMuted, fontSize: 11 },
            splitLine: { lineStyle: { color: DARK_COLORS.border, type: 'dashed' } }
        },
        series: [
            {
                name: '标的数',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                lineStyle: { color: DARK_COLORS.blue, width: 3 },
                itemStyle: { color: DARK_COLORS.blue, borderWidth: 2, borderColor: DARK_COLORS.bg },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(74, 158, 255, 0.3)' },
                        { offset: 1, color: 'rgba(74, 158, 255, 0.05)' }
                    ])
                },
                data: data.map(item => item.symbol_count)
            },
            {
                name: '记录数',
                type: 'line',
                smooth: true,
                symbol: 'circle',
                symbolSize: 6,
                lineStyle: { color: DARK_COLORS.green, width: 3 },
                itemStyle: { color: DARK_COLORS.green, borderWidth: 2, borderColor: DARK_COLORS.bg },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(74, 222, 128, 0.3)' },
                        { offset: 1, color: 'rgba(74, 222, 128, 0.05)' }
                    ])
                },
                data: data.map(item => item.record_count)
            }
        ]
    };
    
    qualityTrendChart.setOption(option);
}

function renderIssueDistributionChart(data) {
    ensureChartInitialized('issue');
    if (!issueDistributionChart) return;
    
    if (!data || data.length === 0) {
        issueDistributionChart.setOption({
            title: {
                text: '暂无异常',
                left: 'center',
                top: 'center',
                textStyle: { color: DARK_COLORS.textMuted, fontSize: 14 }
            }
        });
        return;
    }
    
    const option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            backgroundColor: DARK_COLORS.bgLight,
            borderColor: DARK_COLORS.border,
            borderWidth: 1,
            textStyle: { color: DARK_COLORS.text },
            formatter: '{b}: {c} ({d}%)'
        },
        series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: true,
            itemStyle: {
                borderRadius: 6,
                borderColor: DARK_COLORS.bg,
                borderWidth: 2
            },
            label: {
                show: true,
                fontSize: 11,
                color: DARK_COLORS.textSecondary,
                formatter: '{b}\n{c}'
            },
            labelLine: {
                length: 10,
                length2: 8,
                lineStyle: { color: DARK_COLORS.border }
            },
            data: data
        }]
    };
    
    issueDistributionChart.setOption(option);
}

function renderKlineChart(data) {
    ensureChartInitialized('kline');
    if (!klineChart) return;
    
    if (!data || data.length === 0) {
        klineChart.setOption({
            title: {
                text: '暂无数据',
                left: 'center',
                top: 'center',
                textStyle: { color: DARK_COLORS.textMuted, fontSize: 14 }
            }
        });
        return;
    }
    
    const sortedData = [...data].sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
    
    const dates = sortedData.map(item => item.trade_date);
    const klineData = sortedData.map(item => [
        parseFloat(item.open_price) || 0,
        parseFloat(item.close_price) || 0,
        parseFloat(item.low_price) || 0,
        parseFloat(item.high_price) || 0
    ]);
    const volumes = sortedData.map(item => parseFloat(item.volume) || 0);
    
    const option = {
        backgroundColor: 'transparent',
        animation: false,
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            backgroundColor: DARK_COLORS.bgLight,
            borderColor: DARK_COLORS.border,
            borderWidth: 1,
            textStyle: { color: DARK_COLORS.text },
            formatter: (params) => {
                if (!params || params.length === 0) return '';
                const klineItem = params.find(p => p.seriesName === 'K线');
                if (!klineItem) return '';
                
                const dataIndex = klineItem.dataIndex;
                const item = sortedData[dataIndex];
                
                let color = DARK_COLORS.green;
                const close = parseFloat(item.close_price) || 0;
                const open = parseFloat(item.open_price) || 0;
                if (close < open) {
                    color = DARK_COLORS.red;
                }
                
                return `
                    <div style="font-weight:500; margin-bottom:8px;">${item.trade_date}</div>
                    <div>开盘: ${open.toFixed(2)}</div>
                    <div>收盘: <span style="color:${color};font-weight:bold">${close.toFixed(2)}</span></div>
                    <div>最高: ${(parseFloat(item.high_price) || 0).toFixed(2)}</div>
                    <div>最低: ${(parseFloat(item.low_price) || 0).toFixed(2)}</div>
                    <div>成交量: ${formatVolume(item.volume)}</div>
                `;
            }
        },
        axisPointer: {
            link: [{ xAxisIndex: 'all' }]
        },
        grid: [
            {
                left: '10%',
                right: '5%',
                top: '5%',
                height: '55%'
            },
            {
                left: '10%',
                right: '5%',
                top: '65%',
                height: '25%'
            }
        ],
        xAxis: [
            {
                type: 'category',
                data: dates,
                gridIndex: 0,
                axisLine: { lineStyle: { color: DARK_COLORS.border } },
                axisTick: { show: false },
                axisLabel: {
                    rotate: 45,
                    fontSize: 10,
                    color: DARK_COLORS.textMuted
                },
                splitLine: { show: false }
            },
            {
                type: 'category',
                data: dates,
                gridIndex: 1,
                axisLine: { lineStyle: { color: DARK_COLORS.border } },
                axisTick: { show: false },
                axisLabel: { show: false },
                splitLine: { show: false }
            }
        ],
        yAxis: [
            {
                type: 'value',
                gridIndex: 0,
                scale: true,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    fontSize: 11,
                    color: DARK_COLORS.textMuted,
                    formatter: (value) => parseFloat(value).toFixed(2)
                },
                splitLine: { lineStyle: { color: DARK_COLORS.border, type: 'dashed' } }
            },
            {
                type: 'value',
                gridIndex: 1,
                scale: true,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    fontSize: 11,
                    color: DARK_COLORS.textMuted,
                    formatter: (value) => formatVolume(value)
                },
                splitLine: { lineStyle: { color: DARK_COLORS.border, type: 'dashed' } }
            }
        ],
        dataZoom: [
            {
                type: 'inside',
                xAxisIndex: [0, 1],
                start: 50,
                end: 100
            },
            {
                show: true,
                xAxisIndex: [0, 1],
                type: 'slider',
                bottom: '2%',
                height: 20,
                start: 50,
                end: 100,
                borderColor: DARK_COLORS.border,
                fillerColor: 'rgba(74, 158, 255, 0.2)',
                handleStyle: { color: DARK_COLORS.blue },
                textStyle: { color: DARK_COLORS.textMuted },
                dataBackground: {
                    lineStyle: { color: DARK_COLORS.border },
                    areaStyle: { color: 'rgba(74, 158, 255, 0.1)' }
                }
            }
        ],
        series: [
            {
                name: 'K线',
                type: 'candlestick',
                data: klineData,
                itemStyle: {
                    color: DARK_COLORS.green,
                    color0: DARK_COLORS.red,
                    borderColor: DARK_COLORS.green,
                    borderColor0: DARK_COLORS.red
                }
            },
            {
                name: '成交量',
                type: 'bar',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: volumes.map((vol, index) => {
                    const kline = klineData[index];
                    const isUp = kline && kline[1] >= kline[0];
                    return {
                        value: vol,
                        itemStyle: {
                            color: isUp ? 'rgba(74, 222, 128, 0.5)' : 'rgba(248, 113, 113, 0.5)'
                        }
                    };
                })
            }
        ]
    };
    
    klineChart.setOption(option);
}

function formatVolume(value) {
    if (!value || isNaN(value)) return '-';
    value = parseFloat(value);
    if (value >= 100000000) return (value / 100000000).toFixed(2) + '亿';
    if (value >= 10000) return (value / 10000).toFixed(2) + '万';
    return value.toString();
}

function updateMomentumCharts(data) {
    debouncedUpdateMomentumBar(data);
}

function updateQualityTrendChart(data) {
    debouncedUpdateQualityTrend(data);
}

function updateKlineChart(data) {
    renderKlineChart(data);
    if (klineChart) {
        setTimeout(() => klineChart.resize(), 100);
    }
}

let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        if (momentumBarChart) momentumBarChart.resize();
        if (qualityTrendChart) qualityTrendChart.resize();
        if (klineChart) klineChart.resize();
        if (issueDistributionChart) issueDistributionChart.resize();
    }, 200);
});