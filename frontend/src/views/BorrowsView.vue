<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'

import { listBooksApi } from '@/api/books'
import { createBorrowApi, listBorrowsApi, returnBorrowApi } from '@/api/borrows'
import { extractErrorMessage } from '@/api/http'
import { listReadersApi } from '@/api/readers'
import type { BookOut } from '@/types/book'
import type { BorrowOut, BorrowStatus } from '@/types/borrow'
import type { ReaderOut } from '@/types/reader'

// 借阅管理页，契约见 docs/system-design.md 8.6 与 11.5
const loading = ref(false)
const loadError = ref('')
const borrows = ref<BorrowOut[]>([])
const total = ref(0)

const query = reactive({
  page: 1,
  page_size: 20,
  status: '' as BorrowStatus | '',
  book_id: undefined as number | undefined,
  reader_id: undefined as number | undefined,
  due_before: ''
})

const STATUS_LABEL: Record<BorrowStatus, string> = {
  borrowed: '在借',
  overdue: '逾期',
  returned: '已归还'
}

const STATUS_TAG: Record<BorrowStatus, 'primary' | 'danger' | 'success'> = {
  borrowed: 'primary',
  overdue: 'danger',
  returned: 'success'
}

async function loadBorrows(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await listBorrowsApi({
      page: query.page,
      page_size: query.page_size,
      status: query.status || undefined,
      book_id: query.book_id ?? undefined,
      reader_id: query.reader_id ?? undefined,
      due_before: query.due_before || undefined
    })
    borrows.value = data.items
    total.value = data.total
  } catch (error) {
    borrows.value = []
    total.value = 0
    loadError.value = extractErrorMessage(error)
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  query.page = 1
  void loadBorrows()
}

function handleReset(): void {
  query.status = ''
  query.book_id = undefined
  query.reader_id = undefined
  query.due_before = ''
  query.page = 1
  void loadBorrows()
}

function handlePageChange(page: number): void {
  query.page = page
  void loadBorrows()
}

function handleSizeChange(size: number): void {
  query.page_size = size
  query.page = 1
  void loadBorrows()
}

// 新建借阅对话框
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  book_id: undefined as number | undefined,
  reader_id: undefined as number | undefined,
  due_date: '',
  notes: ''
})

const rules: FormRules<typeof form> = {
  book_id: [{ required: true, message: '请选择图书', trigger: 'change' }],
  reader_id: [{ required: true, message: '请选择读者', trigger: 'change' }]
}

const bookOptions = ref<BookOut[]>([])
const readerOptions = ref<ReaderOut[]>([])
const bookSearching = ref(false)
const readerSearching = ref(false)

async function searchBooks(keyword: string): Promise<void> {
  bookSearching.value = true
  try {
    const { data } = await listBooksApi({
      page: 1,
      page_size: 20,
      keyword: keyword.trim() || undefined,
      available_only: true
    })
    bookOptions.value = data.items
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    bookSearching.value = false
  }
}

async function searchReaders(keyword: string): Promise<void> {
  readerSearching.value = true
  try {
    const { data } = await listReadersApi({
      page: 1,
      page_size: 20,
      keyword: keyword.trim() || undefined,
      status: 'active'
    })
    readerOptions.value = data.items
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    readerSearching.value = false
  }
}

function readerLabel(reader: ReaderOut): string {
  const contact = reader.phone ?? reader.email ?? ''
  return contact ? `${reader.name}（${contact}）` : reader.name
}

function disabledDueDate(date: Date): boolean {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date.getTime() < today.getTime()
}

function openCreate(): void {
  Object.assign(form, {
    book_id: undefined,
    reader_id: undefined,
    due_date: '',
    notes: ''
  })
  dialogVisible.value = true
  void searchBooks('')
  void searchReaders('')
}

async function handleSubmit(): Promise<void> {
  if (formRef.value === undefined) {
    return
  }
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid || form.book_id === undefined || form.reader_id === undefined) {
    return
  }

  submitting.value = true
  try {
    await createBorrowApi({
      book_id: form.book_id,
      reader_id: form.reader_id,
      due_date: form.due_date || undefined,
      notes: form.notes.trim() || undefined
    })
    ElMessage.success('借出成功')
    dialogVisible.value = false
    await loadBorrows()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  } finally {
    submitting.value = false
  }
}

async function handleReturn(borrow: BorrowOut): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定归还《${borrow.book.title}》（读者：${borrow.reader.name}）吗？`,
      '归还确认',
      { type: 'warning', confirmButtonText: '归还', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    await returnBorrowApi(borrow.id)
    ElMessage.success('归还成功')
    await loadBorrows()
  } catch (error) {
    ElMessage.error(extractErrorMessage(error))
  }
}

onMounted(loadBorrows)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h2>借阅管理</h2>
      <el-button type="primary" @click="openCreate">新建借阅</el-button>
    </div>

    <el-form class="filter-bar" inline @submit.prevent="handleSearch">
      <el-form-item label="状态">
        <el-select
          v-model="query.status"
          placeholder="全部"
          clearable
          style="width: 120px"
          @change="handleSearch"
        >
          <el-option label="在借" value="borrowed" />
          <el-option label="逾期" value="overdue" />
          <el-option label="已归还" value="returned" />
        </el-select>
      </el-form-item>
      <el-form-item label="图书 ID">
        <el-input-number
          v-model="query.book_id"
          :min="1"
          placeholder="选填"
          style="width: 130px"
        />
      </el-form-item>
      <el-form-item label="读者 ID">
        <el-input-number
          v-model="query.reader_id"
          :min="1"
          placeholder="选填"
          style="width: 130px"
        />
      </el-form-item>
      <el-form-item label="到期不晚于">
        <el-date-picker
          v-model="query.due_before"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选填"
          style="width: 150px"
          @change="handleSearch"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="borrows" stripe>
      <el-table-column label="图书" min-width="170" show-overflow-tooltip>
        <template #default="{ row }">{{ row.book.title }}</template>
      </el-table-column>
      <el-table-column label="读者" min-width="110">
        <template #default="{ row }">{{ row.reader.name }}</template>
      </el-table-column>
      <el-table-column label="借出时间" width="170">
        <template #default="{ row }">
          {{ new Date(row.borrowed_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column prop="due_date" label="到期日" width="110" />
      <el-table-column label="归还时间" width="170">
        <template #default="{ row }">
          {{ row.returned_at ? new Date(row.returned_at).toLocaleString() : '—' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="STATUS_TAG[row.status as BorrowStatus]">
            {{ STATUS_LABEL[row.status as BorrowStatus] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'returned'"
            type="primary"
            link
            @click="handleReturn(row)"
          >
            归还
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty :description="loadError || '暂无借阅记录'" />
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
      title="新建借阅"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="图书" prop="book_id">
          <el-select
            v-model="form.book_id"
            filterable
            remote
            :remote-method="searchBooks"
            :loading="bookSearching"
            placeholder="搜索书名 / 作者 / ISBN（仅显示可借）"
            style="width: 100%"
          >
            <el-option
              v-for="book in bookOptions"
              :key="book.id"
              :label="`${book.title} · ${book.author}（可借 ${book.available_copies}）`"
              :value="book.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="读者" prop="reader_id">
          <el-select
            v-model="form.reader_id"
            filterable
            remote
            :remote-method="searchReaders"
            :loading="readerSearching"
            placeholder="搜索姓名 / 电话 / 邮箱（仅显示启用）"
            style="width: 100%"
          >
            <el-option
              v-for="reader in readerOptions"
              :key="reader.id"
              :label="readerLabel(reader)"
              :value="reader.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="到期日">
          <el-date-picker
            v-model="form.due_date"
            type="date"
            value-format="YYYY-MM-DD"
            :disabled-date="disabledDueDate"
            placeholder="选填，不早于今天"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.notes"
            type="textarea"
            :rows="3"
            maxlength="500"
            placeholder="选填"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          借出
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
