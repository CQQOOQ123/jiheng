/**
 * Client half of Jiheng: a settings page under Settings → 计算器.
 *
 * Shows live calculator status (from GET /calc/status registered by the Host half)
 * and lets the user switch the tool-usage policy (POST /calc/policy).
 */
window.__ModuleLoader__.load({
  id: '@local/jiheng',
  factory(require) {
    const React = require('react');
    const h = React.createElement;
    const { useCallback, useEffect, useState } = React;

    const POLICIES = [
      { id: 'complex', label: '仅复杂运算时使用', desc: '数组统计、折扣/复利/贷款、单位换算、符号运算、3 步以上、大数、金额时调用；简单四则由模型直接算。' },
      { id: 'always', label: '总是使用', desc: '任何计算都调用计算器，最稳但 token 更多。' },
      { id: 'auto', label: '由模型自己判断', desc: '只给能力描述，由模型决定何时调用。' },
      { id: 'custom', label: '自定义规则', desc: '用自然语言描述触发条件，写进工具描述。' },
      { id: 'never', label: '完全不使用', desc: '不注册工具，模型看不到计算器。' },
    ];

    const LIMIT_FIELDS = [
      { key: 'max_series', label: '序列长度（series 最多多少个值）' },
      { key: 'max_output_items', label: '输出列表条数（超过转摘要）' },
      { key: 'max_expr_chars', label: '表达式字符数' },
      { key: 'max_array_items', label: '数组元素个数' },
      { key: 'exact_only', label: '严格精确（1 开 / 0 关）' },
      { key: 'strict_numeric', label: '严格数值（1=近似则报错 / 0=允许近似）' },
    ];

    const S = {
      page: { padding: '24px 28px', maxWidth: 820, color: 'var(--dsw-alias-label-primary)', fontSize: 13 },
      title: { margin: 0, fontSize: 18, fontWeight: 600 },
      sub: { margin: '4px 0 20px', fontSize: 12, color: 'var(--dsw-alias-label-secondary)' },
      card: { border: '1px solid var(--dsw-alias-border-l1)', borderRadius: 10, background: 'var(--dsw-alias-bg-layer-1)', padding: '16px 18px', marginBottom: 16 },
      cardTitle: { margin: '0 0 12px', fontSize: 13, fontWeight: 600 },
      grid: { display: 'grid', gridTemplateColumns: '110px 1fr', gap: '8px 14px', fontSize: 12.5 },
      key: { color: 'var(--dsw-alias-label-secondary)' },
      badge: (tone) => ({
        display: 'inline-flex', alignItems: 'center', gap: 6, padding: '1px 9px', borderRadius: 999,
        fontSize: 11.5, border: '1px solid var(--dsw-alias-border-l1)',
        color: tone === 'ok' ? 'var(--dsw-alias-state-success-primary)' : 'var(--dsw-alias-label-secondary)',
      }),
      dot: (tone) => ({ width: 6, height: 6, borderRadius: 999, background: tone === 'ok' ? 'var(--dsw-alias-state-success-primary)' : 'var(--dsw-alias-state-idle-primary)' }),
      row: { display: 'flex', gap: 10, alignItems: 'flex-start', padding: '11px 0', borderTop: '1px solid var(--dsw-alias-border-l1)' },
      radio: { marginTop: 2, accentColor: 'var(--dsw-alias-brand-primary)' },
      rowLabel: { fontSize: 13, fontWeight: 500, lineHeight: 1.4 },
      rowDesc: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)', lineHeight: 1.5, marginTop: 2 },
      textarea: {
        width: '100%', boxSizing: 'border-box', marginTop: 10, padding: '8px 10px', borderRadius: 8,
        border: '1px solid var(--dsw-alias-border-l1)', background: 'var(--dsw-alias-bg-base)',
        color: 'inherit', fontSize: 12.5, lineHeight: 1.5, minHeight: 64, resize: 'vertical', fontFamily: 'inherit',
      },
      actions: { display: 'flex', gap: 10, alignItems: 'center', marginTop: 14 },
      primary: (busy) => ({
        padding: '7px 16px', borderRadius: 8, border: 'none', fontSize: 13, cursor: busy ? 'default' : 'pointer',
        background: 'var(--dsw-alias-brand-primary)', color: 'var(--dsw-alias-bg-base)', opacity: busy ? 0.6 : 1,
      }),
      ghost: {
        padding: '7px 14px', borderRadius: 8, fontSize: 13, cursor: 'pointer',
        border: '1px solid var(--dsw-alias-border-l1)', background: 'transparent', color: 'inherit',
      },
      hint: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' },
      error: { marginTop: 10, fontSize: 12, color: 'var(--dsw-alias-state-error-primary)' },
      mono: { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 11.5 },
      numInput: {
        width: 120, marginLeft: 'auto', padding: '5px 8px', borderRadius: 6, fontSize: 12.5,
        border: '1px solid var(--dsw-alias-border-l1)', background: 'var(--dsw-alias-bg-base)', color: 'inherit',
      },
      limitRow: { display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderTop: '1px solid var(--dsw-alias-border-l1)' },
      subTitle: { fontSize: 12, fontWeight: 600, color: 'var(--dsw-alias-label-secondary)', margin: '14px 0 8px' },
      packBlock: { borderTop: '1px solid var(--dsw-alias-border-l1)', padding: '8px 0' },
      packHead: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 },
      packRow: { display: 'flex', alignItems: 'center', gap: 10, fontSize: 12.5, padding: '4px 0' },
      smallBtn: {
        marginLeft: 'auto', padding: '3px 8px', fontSize: 11.5, borderRadius: 5, cursor: 'pointer',
        border: '1px solid var(--dsw-alias-border-l1)', background: 'none', color: 'var(--dsw-alias-label-secondary)',
      },
      formRow: { display: 'flex', gap: 8, marginBottom: 8 },
      select: {
        padding: '6px 8px', borderRadius: 6, fontSize: 12.5,
        border: '1px solid var(--dsw-alias-border-l1)', background: 'var(--dsw-alias-bg-base)', color: 'inherit',
      },
      checkRow: { display: 'flex', alignItems: 'center', gap: 8, margin: '8px 0' },
      formInput: {
        flex: 1, padding: '6px 8px', borderRadius: 6, fontSize: 12.5,
        border: '1px solid var(--dsw-alias-border-l1)', background: 'var(--dsw-alias-bg-base)', color: 'inherit',
      },
    };

    function CalcSettings() {
      const [status, setStatus] = useState(null);
      const [policy, setPolicy] = useState('complex');
      const [rules, setRules] = useState('');
      const [busy, setBusy] = useState(false);
      const [saved, setSaved] = useState(false);
      const [error, setError] = useState('');
      const [limits, setLimits] = useState(null);
      const [limitsBusy, setLimitsBusy] = useState(false);
      const [limitsSaved, setLimitsSaved] = useState(false);
      const [limitsError, setLimitsError] = useState('');
      const [workersMode, setWorkersMode] = useState('1');
      const [customWorkers, setCustomWorkers] = useState('4');
      const [workersBusy, setWorkersBusy] = useState(false);
      const [workersSaved, setWorkersSaved] = useState(false);
      const [workersError, setWorkersError] = useState('');
      const [packs, setPacks] = useState([]);
      const [plugins, setPlugins] = useState([]);
      const [packMsg, setPackMsg] = useState('');
      const [packErr, setPackErr] = useState('');
      const [fPack, setFPack] = useState('ai-formulas');
      const [fName, setFName] = useState('');
      const [fParams, setFParams] = useState('');
      const [fBody, setFBody] = useState('');
      const [fTests, setFTests] = useState('');
      const [fOverwrite, setFOverwrite] = useState(false);

      const load = useCallback(async () => {
        try {
          const res = await fetch('/calc/status', { cache: 'no-store' });
          const data = await res.json();
          if (!data.ok) throw new Error(data.error || 'status failed');
          setStatus(data);
          setPolicy(data.policy);
          setRules(data.customRules || '');
          setLimits(data.limits || {});
          setWorkersMode(String(data.configuredWorkers ?? '1'));
          if (typeof data.configuredWorkers === 'number') setCustomWorkers(String(data.configuredWorkers));
          try {
            const pk = await fetch('/calc/packs', { cache: 'no-store' });
            const pd = await pk.json();
            if (pd.ok) {
              setPacks(pd.packs || []);
              setPlugins(pd.plugins || []);
            }
          } catch {
            /* packs are optional */
          }
          setError('');
        } catch (err) {
          setError(String(err && err.message || err));
        }
      }, []);

      useEffect(() => {
        load();
      }, [load]);

      const save = useCallback(async () => {
        setBusy(true);
        setSaved(false);
        setError('');
        try {
          const res = await fetch('/calc/policy', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ policy, customRules: rules }),
          });
          const data = await res.json();
          if (!res.ok || !data.ok) throw new Error(data.error || ('HTTP ' + res.status));
          setStatus(data);
          setSaved(true);
        } catch (err) {
          setError(String(err && err.message || err));
        } finally {
          setBusy(false);
        }
      }, [policy, rules]);

      const saveLimits = useCallback(async (reset) => {
        setLimitsBusy(true);
        setLimitsSaved(false);
        setLimitsError('');
        try {
          const payload = reset ? { reset: true } : { limits };
          const res = await fetch('/calc/limits', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await res.json();
          if (!res.ok || !data.ok) throw new Error(data.error || ('HTTP ' + res.status));
          setLimits(data.limits);
          setStatus((prev) => (prev ? { ...prev, limits: data.limits } : prev));
          setLimitsSaved(true);
        } catch (err) {
          setLimitsError(String(err && err.message || err));
        } finally {
          setLimitsBusy(false);
        }
      }, [limits]);

      const packCall = useCallback(async (payload) => {
        setPackErr('');
        setPackMsg('');
        const res = await fetch('/calc/packs', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || ('HTTP ' + res.status));
        setPacks(data.packs || []);
        return data;
      }, []);

      const addFormula = useCallback(async () => {
        try {
          const tests = fTests
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean)
            .map((line) => {
              const parts = line.split('=>').map((x) => x.trim());
              return {
                args: parts[0] ? parts[0].split(',').map((x) => x.trim()).filter(Boolean) : [],
                expect: parts[1] || undefined,
              };
            });
          await packCall({
            op: 'add', pack: fPack, name: fName,
            params: fParams.split(',').map((x) => x.trim()).filter(Boolean),
            body: fBody, tests, overwrite: fOverwrite,
          });
          setFName('');
          setFParams('');
          setFBody('');
          setFTests('');
          setFOverwrite(false);
          setPackMsg('已添加并通过自测，立即可用');
        } catch (err) {
          setPackErr(String(err && err.message || err));
        }
      }, [fPack, fName, fParams, fBody, fTests, fOverwrite, packCall]);

      const deleteFormula = useCallback(async (pack, name) => {
        try {
          await packCall({ op: 'delete', pack, name });
          setPackMsg('已删除');
        } catch (err) {
          setPackErr(String(err && err.message || err));
        }
      }, [packCall]);

      const saveWorkers = useCallback(async () => {
        setWorkersBusy(true);
        setWorkersSaved(false);
        setWorkersError('');
        try {
          const res = await fetch('/calc/workers', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({
              workers: workersMode === 'auto'
                ? 'auto'
                : Number(workersMode === 'custom' ? customWorkers : workersMode),
            }),
          });
          const data = await res.json();
          if (!res.ok || !data.ok) throw new Error(data.error || ('HTTP ' + res.status));
          setStatus((prev) => (prev ? { ...prev, workers: data.workers, ready: data.ready, configuredWorkers: data.configuredWorkers } : prev));
          setWorkersSaved(true);
        } catch (err) {
          setWorkersError(String(err && err.message || err));
        } finally {
          setWorkersBusy(false);
        }
      }, [workersMode, customWorkers]);

      const registered = status && status.registered;
      const workerTone = status && status.worker === 'running' ? 'ok' : 'idle';

      return h('div', { style: S.page },
        h('h2', { style: S.title }, '计算器'),
        h('p', { style: S.sub }, '精确有理数 + 符号计算（分数、根号、解方程、求导）。这里控制模型何时使用它。'),

        h('div', { style: S.card },
          h('h3', { style: S.cardTitle }, '状态'),
          status
            ? h('div', { style: S.grid },
                h('span', { style: S.key }, '版本'), h('span', null, status.version),
                h('span', { style: S.key }, '工具'),
                h('span', null,
                  h('span', { style: S.badge(registered ? 'ok' : 'idle') },
                    h('span', { style: S.dot(registered ? 'ok' : 'idle') }),
                    registered ? '已注册' : '未注册')),
                h('span', { style: S.key }, '工作进程'),
                h('span', null,
                  h('span', { style: S.badge(workerTone) },
                    h('span', { style: S.dot(workerTone) }),
                    status.worker === 'running' ? '运行中' : '空闲（首次调用时启动）')),
                h('span', { style: S.key }, '公式目录'), h('span', { style: S.mono }, status.home),
                h('span', { style: S.key }, '能力'), h('span', null, (status.capabilities || []).join(' · ')),
                h('span', { style: S.key }, '能力包'),
                h('span', { style: S.mono }, ((status.packs && status.packs.plugins) || []).join(', ') || '（无）'),
                h('span', { style: S.key }, '公式包'),
                h('span', { style: S.mono }, ((status.packs && status.packs.formulas) || []).join(', ') || '（无）'),
              )
            : h('span', { style: S.hint }, '读取中…')
        ),

        h('div', { style: S.card },
          h('h3', { style: S.cardTitle }, '使用策略'),
          POLICY_ROWS(policy, setPolicy),
          policy === 'custom'
            ? h('textarea', {
                style: S.textarea,
                value: rules,
                placeholder: '例如：只有在涉及金额、税率、折扣时才调用计算器。',
                onChange: (e) => setRules(e.target.value),
              })
            : null,
          h('div', { style: S.actions },
            h('button', { style: S.primary(busy), disabled: busy, onClick: save }, busy ? '保存中…' : '保存'),
            h('button', { style: S.ghost, onClick: load }, '刷新状态'),
            saved ? h('span', { style: S.hint }, '已保存，立即生效') : null,
          ),
          error ? h('div', { style: S.error }, error) : null,
        ),

        h('div', { style: S.card },
          h('h3', { style: S.cardTitle }, '限额'),
          h('p', { style: S.hint }, '超过限额会报错或自动转摘要；可随时恢复默认。'),
          limits
            ? h('div', null, LIMIT_FIELDS.map((field) =>
                h('label', { key: field.key, style: S.limitRow },
                  h('span', { style: S.rowLabel }, field.label),
                  h('input', {
                    type: 'number',
                    style: S.numInput,
                    value: limits[field.key] === undefined ? '' : limits[field.key],
                    onChange: (e) => setLimits({ ...limits, [field.key]: e.target.value }),
                  }),
                ),
              ))
            : h('span', { style: S.hint }, '读取中…'),
          h('div', { style: S.actions },
            h('button', { style: S.primary(limitsBusy), disabled: limitsBusy, onClick: () => saveLimits(false) },
              limitsBusy ? '保存中…' : '保存限额'),
            h('button', { style: S.ghost, onClick: () => saveLimits(true) }, '恢复默认'),
            limitsSaved ? h('span', { style: S.hint }, '已保存，立即生效') : null,
          ),
          limitsError ? h('div', { style: S.error }, limitsError) : null,
        ),

        h('div', { style: S.card },
          h('h3', { style: S.cardTitle }, '工作进程（worker 池）'),
          h('p', { style: S.hint },
            '默认 1 个；每个约 52MB。可固定 1–' + String((status && status.maxWorkers) || 8)
            + ' 个，或 auto 按并发自动扩展；选“自定义”可填任意数量。'),
          status
            ? h('div', { style: S.grid },
                h('span', { style: S.key }, '运行中'), h('span', null, String(status.workers || 0)),
                h('span', { style: S.key }, '就绪'), h('span', null, String(status.ready ?? 0)),
                h('span', { style: S.key }, '配置'), h('span', null, String(status.configuredWorkers)),
              )
            : h('span', { style: S.hint }, '读取中…'),
          h('div', { style: S.actions },
            h('select', {
              style: S.select,
              value: workersMode,
              onChange: (e) => setWorkersMode(e.target.value),
            }, Array.from({ length: (status && status.maxWorkers) || 8 }, (_, i) => String(i + 1))
              .map((value) => h('option', { key: value, value }, value + ' 个'))
              .concat([
                h('option', { key: 'auto', value: 'auto' }, '自动'),
                h('option', { key: 'custom', value: 'custom' }, '自定义'),
              ])),
            workersMode === 'custom'
              ? h('input', {
                  type: 'number',
                  style: S.numInput,
                  min: 1,
                  max: (status && status.maxWorkers) || 8,
                  value: customWorkers,
                  onChange: (e) => setCustomWorkers(e.target.value),
                })
              : null,
            h('button', { style: S.primary(workersBusy), disabled: workersBusy, onClick: saveWorkers },
              workersBusy ? '保存中…' : '保存'),
            workersSaved ? h('span', { style: S.hint }, '已生效') : null,
          ),
          workersError ? h('div', { style: S.error }, workersError) : null,
        ),

        h('div', { style: S.card },
          h('h3', { style: S.cardTitle }, '公式与能力包'),
          h('p', { style: S.hint }, 'AI 或人都可以在这里添加/删除公式；保存后立即生效。'),

          h('div', { style: S.subTitle }, '公式包'),
          packs.length === 0
            ? h('span', { style: S.hint }, '（还没有公式包）')
            : h('div', null, packs.map((pack) =>
                h('div', { key: pack.file, style: S.packBlock },
                  h('div', { style: S.packHead },
                    h('span', { style: S.mono }, pack.file + ' (v' + (pack.version || 1) + ')'),
                    h('button', { style: S.smallBtn, onClick: () => deleteFormula(pack.file.replace(/\.json$/, '')) }, '删除整包'),
                  ),
                  (pack.fn || []).map((fn) =>
                    h('div', { key: fn.name, style: S.packRow },
                      h('span', null, fn.name + '(' + (fn.params || []).join(', ') + ')'),
                      h('span', { style: S.mono }, fn.body),
                      h('button', { style: S.smallBtn, onClick: () => deleteFormula(pack.file.replace(/\.json$/, ''), fn.name) }, '删除'),
                    ),
                  ),
                ),
              )),

          h('div', { style: S.subTitle }, '添加公式'),
          h('div', { style: S.formRow },
            h('input', { style: S.formInput, placeholder: '包名', value: fPack, onChange: (e) => setFPack(e.target.value) }),
            h('input', { style: S.formInput, placeholder: '函数名', value: fName, onChange: (e) => setFName(e.target.value) }),
            h('input', { style: S.formInput, placeholder: '参数（逗号分隔）', value: fParams, onChange: (e) => setFParams(e.target.value) }),
          ),
          h('input', { style: S.formInput, placeholder: '公式，例如 x*(1+0.13)', value: fBody, onChange: (e) => setFBody(e.target.value) }),
          h('textarea', {
            style: S.textarea,
            value: fTests,
            placeholder: '自测（可选，每行一条）：参数,参数 => 期望值，例如 1000,0.13 => 1130',
            onChange: (e) => setFTests(e.target.value),
          }),
          h('label', { style: S.checkRow },
            h('input', { type: 'checkbox', checked: fOverwrite, onChange: (e) => setFOverwrite(e.target.checked) }),
            h('span', { style: S.hint }, '覆盖同名（公式体变化时）'),
          ),
          h('div', { style: S.actions },
            h('button', { style: S.primary(false), onClick: addFormula }, '添加'),
            packMsg ? h('span', { style: S.hint }, packMsg) : null,
          ),
          packErr ? h('div', { style: S.error }, packErr) : null,

          h('div', { style: S.subTitle }, '能力包（Python）'),
          plugins.length === 0
            ? h('span', { style: S.hint }, '（无）')
            : h('div', { style: S.mono }, plugins.join(', ')),
        ),
      );
    }

    function POLICY_ROWS(policy, setPolicy) {
      return h('div', null, POLICIES.map((item, index) =>
        h('label', {
          key: item.id,
          style: index === 0 ? { ...S.row, borderTop: 'none' } : S.row,
        },
          h('input', {
            type: 'radio', name: 'calc-policy', style: S.radio,
            checked: policy === item.id,
            onChange: () => setPolicy(item.id),
          }),
          h('span', null,
            h('span', { style: S.rowLabel }, item.label),
            h('span', { style: S.rowDesc }, item.desc),
          ),
        )
      ));
    }

    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.slots.inject('settings.section', () => ctx.slots.register({
          name: 'settings.section', id: 'jiheng', order: 20, label: '计算器',
        }, CalcSettings));
      },
    };
  },
});
