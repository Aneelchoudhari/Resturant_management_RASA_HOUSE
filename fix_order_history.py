import re

path = r'C:/Users/anils/OneDrive/Desktop/restaurant_management/frontend/src/pages/OrderHistory.jsx'
content = open(path, encoding='utf-8').read()

# Lines 139-146 contain the action cell. Replace by line range.
lines = content.splitlines(keepends=True)

new_lines = []
i = 0
while i < len(lines):
    # Detect the old action cell start at line 139 (0-indexed: 138)
    if i == 138:
        # Skip lines 138-145 (0-indexed) = old action cell
        new_lines.append('                    <td>\n')
        new_lines.append("                       <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>\n")
        new_lines.append('                         {canChangeStatus && (\n')
        new_lines.append('                           <select value={o.status} onChange={(e) => changeStatus(o.id, e.target.value)} aria-label={`Status for order ${o.id}`}>\n')
        new_lines.append('                             {allowedStatuses.map((status) => <option key={status} value={status}>{status}</option>)}\n')
        new_lines.append('                           </select>\n')
        new_lines.append('                         )}\n')
        new_lines.append("                         {canMarkPaid && o.payment_status !== 'paid' && (\n")
        new_lines.append('                           <button className="btn btn-success" onClick={() => pay(o.id, \'cash\')}>Mark Cash Paid</button>\n')
        new_lines.append('                         )}\n')
        new_lines.append('                         {!canChangeStatus && !canMarkPaid && (\n')
        new_lines.append("                           <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>View only</span>\n")
        new_lines.append('                         )}\n')
        new_lines.append('                       </div>\n')
        new_lines.append('                    </td>\n')
        i += 8  # skip lines 138-145
    else:
        new_lines.append(lines[i])
        i += 1

open(path, 'w', encoding='utf-8').write(''.join(new_lines))
print('Done')
