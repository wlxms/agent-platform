import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Button,
  Card,
  Col,
  Empty,
  Input,
  Menu,
  Pagination,
  Row,
  Spin,
  Tag,
  Typography,
} from 'antd';
import { RobotOutlined, SearchOutlined } from '@ant-design/icons';
import { marketApi } from '@/api/market';
import type { MarketCategory, Template } from '@/types';

const { Text, Title, Paragraph } = Typography;

// ─── Helpers ──────────────────────────────────────────────────────

function formatUsage(count: number): string {
  if (count >= 10_000) return `${(count / 10_000).toFixed(1)}w 次使用`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}k 次使用`;
  return `${count} 次使用`;
}

// ─── Component ────────────────────────────────────────────────────

export default function MarketHome() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const categoryId = searchParams.get('category') ?? '';
  const keyword = searchParams.get('keyword') ?? '';
  const page = Number(searchParams.get('page') ?? 1);
  const pageSize = 12;

  const [categories, setCategories] = useState<MarketCategory[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [catLoading, setCatLoading] = useState(false);

  // ─── Fetch categories ───────────────────────────────────────────

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setCatLoading(true);
      try {
        const res = await marketApi.getCategories();
        if (!cancelled) setCategories(res.data ?? []);
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setCatLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // ─── Fetch templates ────────────────────────────────────────────

  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const res = await marketApi.getTemplates({
        category: categoryId || undefined,
        keyword: keyword || undefined,
        page,
        page_size: pageSize,
      });
      setTemplates(res.items ?? []);
      setTotal(res.total ?? 0);
    } catch {
      setTemplates([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [categoryId, keyword, page, pageSize]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  // ─── Handlers ───────────────────────────────────────────────────

  const handleCategoryClick = useCallback((id: string | null) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('page');
      if (id) {
        next.set('category', id);
      } else {
        next.delete('category');
      }
      return next;
    });
  }, [setSearchParams]);

  const handleSearch = useCallback((val: string) => {
    const trimmed = val.trim();
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('page');
      if (trimmed) {
        next.set('keyword', trimmed);
      } else {
        next.delete('keyword');
      }
      return next;
    });
  }, [setSearchParams]);

  const handlePageChange = useCallback((p: number) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('page', String(p));
      return next;
    });
  }, [setSearchParams]);

  // ─── Menu keys ──────────────────────────────────────────────────

  const menuItems = [
    { key: '__all__', label: '全部' },
    ...categories.map((c) => ({ key: c.id, label: c.name })),
  ];
  const activeKey = categoryId || '__all__';

  // ─── Render ─────────────────────────────────────────────────────

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%', padding: 16, background: 'var(--oh-bg)' }}>
      {/* Left sidebar - categories */}
      <div
        style={{
          width: 200,
          flexShrink: 0,
          background: 'var(--oh-surface)',
          borderRadius: 12,
          border: '1px solid var(--oh-border)',
          overflow: 'auto',
        }}
      >
        <Spin spinning={catLoading}>
          <Menu
            mode="inline"
            selectedKeys={[activeKey]}
            items={menuItems}
            onClick={({ key }) => handleCategoryClick(key === '__all__' ? null : key)}
            style={{ border: 'none', background: 'transparent' }}
          />
        </Spin>
      </div>

      {/* Main content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Search bar */}
        <div style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜索模板..."
            allowClear
            enterButton={<><SearchOutlined /> 搜索</>}
            defaultValue={keyword}
            onSearch={handleSearch}
            style={{ maxWidth: 480 }}
          />
        </div>

        {/* Template grid */}
        <Spin spinning={loading}>
          {templates.length === 0 && !loading ? (
            <Empty description="暂无模板" />
          ) : (
            <>
              <Row gutter={[16, 16]}>
                {templates.map((t) => (
                  <Col key={t.id} xs={24} sm={12} md={8} lg={6}>
                    <Card
                      hoverable
                      style={{
                        borderRadius: 12,
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        border: '1px solid var(--oh-border)',
                      }}
                      styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column' } }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                        <div
                          style={{
                            width: 40,
                            height: 40,
                            borderRadius: 8,
                            background: 'var(--oh-surface)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 20,
                            color: 'var(--oh-primary)',
                            flexShrink: 0,
                          }}
                        >
                          <RobotOutlined />
                        </div>
                        <Title level={5} style={{ margin: 0, color: 'var(--oh-text)' }}>
                          {t.name}
                        </Title>
                      </div>

                      <Paragraph
                        type="secondary"
                        ellipsis={{ rows: 2 }}
                        style={{
                          marginBottom: 12,
                          flex: 1,
                          color: 'var(--oh-text-secondary)',
                          fontSize: 13,
                        }}
                      >
                        {t.description}
                      </Paragraph>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                        {t.category_name && (
                          <Tag color="blue">{t.category_name}</Tag>
                        )}
                        <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
                          {formatUsage(t.usage_count)}
                        </Text>
                      </div>

                      <Button
                        type="primary"
                        block
                        onClick={() => navigate(`/agents/new?template_id=${t.id}`)}
                      >
                        使用模板
                      </Button>
                    </Card>
                  </Col>
                ))}
              </Row>

              {/* Pagination */}
              {total > pageSize && (
                <div style={{ display: 'flex', justifyContent: 'center', marginTop: 24 }}>
                  <Pagination
                    current={page}
                    pageSize={pageSize}
                    total={total}
                    onChange={handlePageChange}
                    showSizeChanger={false}
                  />
                </div>
              )}
            </>
          )}
        </Spin>
      </div>
    </div>
  );
}
