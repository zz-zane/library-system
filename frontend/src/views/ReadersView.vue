<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { extractErrorMessage } from '@/api/http'
import {
  createReaderApi,
  deleteReaderApi,
  listReadersApi,
  updateReaderApi
} from '@/api/readers'
import type { ReaderOut, ReaderStatus } from '@/types/reader'

// 读者管理页，契约见 docs/system-design.md 8.5 与 11.5
const loading = ref(false)
const loadError = ref('')
const readers = ref<ReaderOut[]>([])
const total = ref(0)

const query = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  status: '' as ReaderStatus | ''
})

async function loadReaders(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await listReadersApi({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword.trim() || undefined,
      status: query.status || undefined
    })
    readers.value = data.items
    total.value = data.total
  } catch (error) {
    readers.value = []
    total.value = 0
    loadError.value = extractErrorMessage(error)
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  query.page = 1
  void loadReaders()
}

function handleReset(): void {
  query.keyword = ''
  query.status = ''
  query.page = 1
  void loadReaders()
}

function handlePageChange(page: number): void {
  query.page = page
  void loadReaders()
}

function handleSizeChange(size: number): void {
  query.page_size = size
  query.page = 1
  void loadReaders()
}

// 新增 / 编辑对话框
const dialogVisible = ref(false)
const dialogTitle = ref('')
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  phone: '',
  email: '',
  status: 'active' as ReaderStatus,
  notes: ''
})

const rules: FormRules<typeof form> = {
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    { max: 50, message: '姓名不能超过 50 字', trigger: 'blur' }
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }]
}

function openCreate(): void {
  editingId.value = null
  dialogTitle.value = '新增读者'
  Object.assign(form, { name: '', phone: '', email: '', status: 'active', notes: '' })
  dialogVisible.value = true
}

function openEdit(reader: ReaderOut): void {
  editingId.value = reader.id
  dialogTitle.value = '编辑读者'
  Object.assign(form, {
    name: reader.name,
    phone: reader.phone ?? '',
    email: reader.email ?? '',
    status: reader.status,
    notes: reader.notes ?? ''
  })
  dialogVisible.value = true
}

async function handleSubmit(): Promise<void> {
  if (formRef.value === undefined) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) {
    return
  }
  if (!form.phone.trim() && !form.email.trim()) {
    ElMessage.warning('电话和邮箱至少填写一项')
    return
  }

  const payload = {
    name: form.name.trim(),
    phone: form.phone.trim() || undefined,
    email: form.email.trim() || undefined,
    notes: form.notes.trim() || undefined
  }

  submitting.value = true
  try {
    if (editingId.value === null) {
      await createReaderApi(payload)
      ElMessage.success('读者创建成功')
    } else {
      await updateReaderApi(editingId.value, { ...payload, status: form.status })
      ElMessage.success('读者更新成功')
    }
    dialogVisible.value = false
    await loadReaders()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(reader: ReaderOut): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除读者「${reader.name}」吗？存在借阅历史时将被拒绝，可改为停用。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await deleteReaderApi(reader.id)
    ElMessage.success('读者已删除')
    if (readers.value.length === 1 && query.page > 1) {
      query.page -= 1
    }
    await loadReaders()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  }
}

onMounted(loadReaders)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h2>读者管理</h2>
      <el-button type="primary" @click="openCreate">新增读者</el-button>
    </div>

    <el-form class="filter-bar" inline @submit.prevent="handleSearch">
      <el-form-item label="关键词">
        <el-input
          v-model="query.keyword"
          placeholder="姓名 / 电话 / 邮箱"
          clearable
          style="width: 220px"
          @clear="handleSearch"
        />
      </el-form-item>
      <el-form-item label="状态">
        <el-select
          v-model="query.status"
          placeholder="全部"
          clearable
          style="width: 120px"
          @change="handleSearch"
        >
          <el-option label="启用" value="active" />
          <el-option label="停用" value="disabled" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="readers" stripe>
      <el-table-column prop="name" label="姓名" min-width="120" />
      <el-table-column prop="phone" label="电话" min-width="140">
        <template #default="{ row }">{{ row.phone ?? '—' }}</template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.email ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty :description="loadError || '暂无读者数据'" />
      </template>
    </el-table>

    <el-pagination
      class="pagination"
      background
      layout="total, sizes, prev, pager, next"
      :total="total"
      :current-page="query.page"
      :page-size="query.page_size"
      :page-sizes="[10, 20, 50]"
      @current-change="handlePageChange"
      @size-change="handleSizeChange"
    />

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" maxlength="50" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" maxlength="32" placeholder="与邮箱至少填一项" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" maxlength="254" placeholder="与电话至少填一项" />
        </el-form-item>
        <el-form-item v-if="editingId !== null" label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="active">启用</el-radio>
            <el-radio value="disabled">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.notes"
            type="textarea"
            :rows="3"
            maxlength="2000"
            placeholder="选填"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          保存
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.page {
  padding: 24px;
  background: #fff;
  border-radius: 8px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
}

.filter-bar {
  margin-bottom: 8px;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
