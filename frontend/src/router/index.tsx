import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { Spin } from 'antd';
import MainLayout from '@/layouts/MainLayout';
import AuthGuard from '@/components/AuthGuard';
import RoleGuard from '@/components/RoleGuard';
import type { UserRole } from '@/types';

const Login = lazy(() => import('@/pages/login'));
const Dashboard = lazy(() => import('@/pages/dashboard'));
const AgentList = lazy(() => import('@/pages/agents/AgentList'));
const NewAgent = lazy(() => import('@/pages/agents/NewAgent'));
const AgentDetail = lazy(() => import('@/pages/agents/AgentDetail'));
const MarketHome = lazy(() => import('@/pages/market/MarketHome'));
const TemplateDetail = lazy(() => import('@/pages/market/TemplateDetail'));
const SkillStore = lazy(() => import('@/pages/market/SkillStore'));
const McpStore = lazy(() => import('@/pages/market/McpStore'));
const BuilderList = lazy(() => import('@/pages/builder/BuilderList'));
const BuilderEditor = lazy(() => import('@/pages/builder/BuilderEditor'));
const BuilderNew = lazy(() => import('@/pages/builder/BuilderNew'));
const BillingOverview = lazy(() => import('@/pages/billing/BillingOverview'));
const BillRecords = lazy(() => import('@/pages/billing/BillRecords'));
const BudgetManagement = lazy(() => import('@/pages/billing/BudgetManagement'));
const OrgTree = lazy(() => import('@/pages/org/OrgTree'));
const MemberManagement = lazy(() => import('@/pages/org/MemberManagement'));
const ApiKeyManagement = lazy(() => import('@/pages/org/ApiKeyManagement'));
const PermissionConfig = lazy(() => import('@/pages/org/PermissionConfig'));
const ApprovalList = lazy(() => import('@/pages/approvals/ApprovalList'));
const ApprovalHistory = lazy(() => import('@/pages/approvals/ApprovalHistory'));
const MemoryBrowser = lazy(() => import('@/pages/memory/MemoryBrowser'));
const MemorySearch = lazy(() => import('@/pages/memory/MemorySearch'));
const Forbidden = lazy(() => import('@/pages/error/Forbidden'));

function LazyFallback() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
      <Spin size="large" />
    </div>
  );
}

function WithSuspense({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LazyFallback />}>{children}</Suspense>;
}

const adminRoles: UserRole[] = ['super_admin', 'org_admin', 'team_admin'];
const superAdminRoles: UserRole[] = ['super_admin'];

export const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <WithSuspense>
        <Login />
      </WithSuspense>
    ),
  },
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    element: (
      <AuthGuard>
        <MainLayout />
      </AuthGuard>
    ),
    children: [
      { path: 'dashboard', element: <WithSuspense><Dashboard /></WithSuspense> },
      { path: 'agents', element: <WithSuspense><AgentList /></WithSuspense> },
      { path: 'agents/new', element: <WithSuspense><NewAgent /></WithSuspense> },
      { path: 'agents/:id', element: <WithSuspense><AgentDetail /></WithSuspense> },
      { path: 'market', element: <WithSuspense><MarketHome /></WithSuspense> },
      { path: 'market/templates/:id', element: <WithSuspense><TemplateDetail /></WithSuspense> },
      { path: 'market/skills', element: <WithSuspense><SkillStore /></WithSuspense> },
      { path: 'market/mcps', element: <WithSuspense><McpStore /></WithSuspense> },
      { path: 'builder', element: <WithSuspense><BuilderList /></WithSuspense> },
      { path: 'builder/new', element: <WithSuspense><BuilderNew /></WithSuspense> },
      { path: 'builder/:id', element: <WithSuspense><BuilderEditor /></WithSuspense> },
      { path: 'billing', element: <WithSuspense><BillingOverview /></WithSuspense> },
      { path: 'billing/records', element: <WithSuspense><BillRecords /></WithSuspense> },
      {
        path: 'billing/budget',
        element: (
          <RoleGuard allowedRoles={adminRoles}>
            <WithSuspense><BudgetManagement /></WithSuspense>
          </RoleGuard>
        ),
      },
      {
        path: 'org',
        element: (
          <RoleGuard allowedRoles={adminRoles}>
            <WithSuspense><OrgTree /></WithSuspense>
          </RoleGuard>
        ),
      },
      {
        path: 'org/:id/members',
        element: (
          <RoleGuard allowedRoles={adminRoles}>
            <WithSuspense><MemberManagement /></WithSuspense>
          </RoleGuard>
        ),
      },
      {
        path: 'org/:id/api-keys',
        element: (
          <RoleGuard allowedRoles={adminRoles}>
            <WithSuspense><ApiKeyManagement /></WithSuspense>
          </RoleGuard>
        ),
      },
      {
        path: 'permissions',
        element: (
          <RoleGuard allowedRoles={superAdminRoles}>
            <WithSuspense><PermissionConfig /></WithSuspense>
          </RoleGuard>
        ),
      },
      {
        path: 'approvals',
        element: (
          <RoleGuard allowedRoles={adminRoles}>
            <WithSuspense><ApprovalList /></WithSuspense>
          </RoleGuard>
        ),
      },
      {
        path: 'approvals/history',
        element: (
          <RoleGuard allowedRoles={adminRoles}>
            <WithSuspense><ApprovalHistory /></WithSuspense>
          </RoleGuard>
        ),
      },
      { path: 'memory', element: <WithSuspense><MemoryBrowser /></WithSuspense> },
      { path: 'memory/search', element: <WithSuspense><MemorySearch /></WithSuspense> },
      { path: '403', element: <WithSuspense><Forbidden /></WithSuspense> },
    ],
  },
]);
