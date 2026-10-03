function NotificationTabs({ tabs, activeTab, onChange }) {
  return <div className="overflow-x-auto border-b border-[var(--color-border)]"><div className="flex min-w-max justify-between gap-5" role="tablist" aria-label="Notification filters">{tabs.map((tab) => <button key={tab} type="button" role="tab" aria-selected={activeTab === tab} onClick={() => onChange(tab)} className={`min-h-12 border-b-[3px] px-2 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] ${activeTab === tab ? 'border-[#53b5eb] text-[#55b7ee]' : 'border-transparent text-[var(--color-text)] hover:text-white'}`}>{tab}</button>)}</div></div>
}

export default NotificationTabs
