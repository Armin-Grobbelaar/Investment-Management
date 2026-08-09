"use client";
import {
  Container, Paper, Grid, Typography, Box, FormControl, InputLabel,
  Select, MenuItem, TextField, Button, IconButton, Dialog, DialogActions,
  DialogContent, DialogContentText, DialogTitle, Snackbar, Alert, Chip,
  Tooltip, Autocomplete, Divider, Badge, LinearProgress, Stack
} from "@mui/material";
import axios from 'axios';
import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import KeyboardBackspaceIcon from '@mui/icons-material/KeyboardBackspace';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import EditIcon from '@mui/icons-material/Edit';
import CancelIcon from '@mui/icons-material/Cancel';
import SaveIcon from '@mui/icons-material/Save';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import UndoIcon from '@mui/icons-material/Undo';
import RefreshIcon from '@mui/icons-material/Refresh';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { ThemeProvider } from '@mui/material/styles';
import CircularProgress from '@mui/material/CircularProgress';
import { SelectChangeEvent } from '@mui/material/Select';
import { brandingDarkTheme, brandingLightTheme } from '../Themes/muiTheme';
import DrawerComponent from '../Reusable Components/Drawers/SideMenyDrawer';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Column { name: string; type: string; }
interface Row { [key: string]: any; id: number; }
interface TableData {
  columns: Column[];
  data: Row[];
  total: number;
  total_count?: number;
  skip: number;
  limit: number;
}

interface PendingChange {
  id: string;          // unique change id
  kind: 'edit' | 'add' | 'delete';
  rowKey: string;
  data: Row;
  label: string;       // human-readable summary
}

interface InvestmentOption { id: number; label: string; }

interface SnackItem {
  key: number;
  message: string;
  severity: 'success' | 'error' | 'info' | 'warning';
}

// ─── Editable cell component ─────────────────────────────────────────────────

function EditableCell({
  column, value, onChange, investments, readOnly
}: {
  column: Column;
  value: any;
  onChange: (v: any) => void;
  investments: InvestmentOption[];
  readOnly?: boolean;
}) {
  if (readOnly) return <span>{value != null ? String(value) : '—'}</span>;

  const colLower = column.name.toLowerCase();

  // investment_id → searchable dropdown of real investments
  if (colLower === 'investment_id' && investments.length > 0) {
    const current = investments.find(i => i.id === value) || null;
    return (
      <Autocomplete
        size="small"
        options={investments}
        value={current}
        getOptionLabel={o => `${o.id} – ${o.label}`}
        onChange={(_, v) => onChange(v ? v.id : 0)}
        renderInput={params => (
          <TextField {...params} placeholder="Select investment…" size="small" />
        )}
        sx={{ minWidth: 220 }}
        isOptionEqualToValue={(o, v) => o.id === v.id}
      />
    );
  }

  if (column.type === 'date' || column.type === 'timestamp') {
    const dateVal = value
      ? (() => { try { return new Date(value).toISOString().split('T')[0]; } catch { return ''; } })()
      : '';
    return (
      <TextField
        type="date"
        size="small"
        value={dateVal}
        onChange={e => onChange(e.target.value)}
        fullWidth
        slotProps={{ inputLabel: { shrink: true } }}
      />
    );
  }

  if (column.type === 'integer') {
    if (colLower === 'id') return <Typography variant="body2" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>auto</Typography>;
    return (
      <TextField
        type="number"
        size="small"
        value={value ?? ''}
        onChange={e => onChange(parseInt(e.target.value) || 0)}
        fullWidth
        slotProps={{ htmlInput: { step: 1 } }}
      />
    );
  }

  if (column.type === 'float' || column.type === 'numeric') {
    return (
      <TextField
        type="number"
        size="small"
        value={value ?? ''}
        onChange={e => onChange(parseFloat(e.target.value) || 0)}
        fullWidth
        slotProps={{ htmlInput: { step: 'any' } }}
      />
    );
  }

  return (
    <TextField
      size="small"
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      fullWidth
    />
  );
}

// ─── Table Row Component ──────────────────────────────────────────────────────

function DataRow({
  row, columns, isEditing, isDeleted, isAdded, isEdited,
  editData, onFieldChange, onEdit, onDelete, investments,
  disabled,
}: {
  row: Row; columns: Column[]; isEditing: boolean; isDeleted: boolean;
  isAdded: boolean; isEdited: boolean; editData: Row;
  onFieldChange: (f: string, v: any) => void;
  onEdit: () => void; onDelete: () => void;
  investments: InvestmentOption[];
  disabled: boolean;
}) {
  const bgColor = isEditing ? '#e8f5e9' : isDeleted ? '#ffebee' : isAdded ? '#fff3e0' : isEdited ? '#e3f2fd' : 'transparent';
  const opacity = isDeleted ? 0.6 : 1;

  return (
    <tr style={{ backgroundColor: bgColor, opacity, transition: 'background-color 0.2s' }}>
      {columns.map(col => (
        <td key={col.name} style={{ padding: '10px 12px', borderBottom: '1px solid #e0e0e0', verticalAlign: 'middle' }}>
          {isEditing ? (
            col.name.toLowerCase() === 'id' ? (
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>{row[col.name]}</Typography>
            ) : (
              <EditableCell
                column={col}
                value={editData[col.name] ?? ''}
                onChange={v => onFieldChange(col.name, v)}
                investments={investments}
              />
            )
          ) : (
            <Typography variant="body2" noWrap sx={{ maxWidth: 250 }} title={String(row[col.name] ?? '')}>
              {row[col.name] != null ? String(row[col.name]) : <span style={{ color: '#999' }}>—</span>}
            </Typography>
          )}
        </td>
      ))}
      <td style={{ padding: '6px 12px', borderBottom: '1px solid #e0e0e0', whiteSpace: 'nowrap' }}>
        {isEditing ? (
          <Chip label="Editing…" color="success" size="small" variant="outlined" />
        ) : isDeleted ? (
          <Chip label="🗑 Pending delete" color="error" size="small" />
        ) : isAdded ? (
          <Chip label="✚ Pending add" color="warning" size="small" />
        ) : isEdited ? (
          <Chip label="✏ Pending edit" color="info" size="small" />
        ) : (
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Tooltip title="Edit row">
              <span>
                <IconButton color="primary" onClick={onEdit} size="small" disabled={disabled}>
                  <EditIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title="Delete row">
              <span>
                <IconButton color="error" onClick={onDelete} size="small" disabled={disabled}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          </Box>
        )}
      </td>
    </tr>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

function EditData() {
  const router = useRouter();

  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [tableData, setTableData] = useState<TableData | null>(null);
  const [investments, setInvestments] = useState<InvestmentOption[]>([]);

  const [editMode, setEditMode] = useState(false);
  const [editedData, setEditedData] = useState<Row>({} as Row);
  const [editingRowKey, setEditingRowKey] = useState<string | null>(null);
  const [addingNew, setAddingNew] = useState(false);

  // Pending changes as ordered list (for undo)
  const [pendingChanges, setPendingChanges] = useState<PendingChange[]>([]);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [darkMode, setDarkMode] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ rowKey: string; row: Row } | null>(null);

  const [errorDetails, setErrorDetails] = useState<string[]>([]);
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);

  const [snacks, setSnacks] = useState<SnackItem[]>([]);
  const [snackOpen, setSnackOpen] = useState(false);
  const [activeSnack, setActiveSnack] = useState<SnackItem | null>(null);

  // ── Snack queue ──────────────────────────────────────────────────────────

  const showSnack = useCallback((message: string, severity: SnackItem['severity'] = 'success') => {
    setSnacks(prev => [...prev, { key: Date.now(), message, severity }]);
  }, []);

  useEffect(() => {
    if (snacks.length > 0 && !snackOpen) {
      setActiveSnack(snacks[0]);
      setSnacks(prev => prev.slice(1));
      setSnackOpen(true);
    }
  }, [snacks, snackOpen]);

  const handleSnackClose = (_: any, reason?: string) => {
    if (reason === 'clickaway') return;
    setSnackOpen(false);
  };

  // ── Data fetching ────────────────────────────────────────────────────────

  useEffect(() => { fetchTables(); fetchInvestments(); }, []);
  useEffect(() => { if (selectedTable) fetchTableData(); }, [selectedTable, searchQuery]);

  const fetchTables = async () => {
    try {
      const res = await axios.get('/api/edit_data/tables/Investments');
      setTables(res.data.tables || []);
    } catch { showSnack('Failed to load table list', 'error'); }
  };

  const fetchInvestments = async () => {
    try {
      const res = await axios.get('/api/edit_data/table/Investments/investments', { params: { limit: 1000 } });
      const opts: InvestmentOption[] = (res.data.data || []).map((r: any) => ({
        id: r.id,
        label: r.investment_name || `ID ${r.id}`,
      }));
      setInvestments(opts);
    } catch { /* investments dropdown is optional */ }
  };

  const fetchTableData = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`/api/edit_data/table/Investments/${selectedTable}`, {
        params: { search: searchQuery || undefined, limit: 2000 }
      });
      setTableData(res.data);
    } catch (e: any) {
      showSnack(`Failed to load ${selectedTable}: ${e?.response?.data?.detail || e.message}`, 'error');
    } finally { setLoading(false); }
  };

  // ── State helpers ────────────────────────────────────────────────────────

  const rowKey = (row: Row, index: number) => `${row.id}-${index}`;

  const resetEdit = () => {
    setEditMode(false);
    setEditedData({} as Row);
    setEditingRowKey(null);
    setAddingNew(false);
  };

  const cancelAll = () => {
    resetEdit();
    setPendingChanges([]);
    showSnack('All pending changes cancelled', 'info');
  };

  const undoLast = () => {
    setPendingChanges(prev => {
      const last = prev[prev.length - 1];
      if (!last) return prev;
      showSnack(`Undid: ${last.label}`, 'info');
      return prev.slice(0, -1);
    });
  };

  // ── Edit / Add / Delete ──────────────────────────────────────────────────

  const startEdit = (row: Row, index: number) => {
    resetEdit();
    setEditMode(true);
    setEditedData({ ...row });
    setEditingRowKey(rowKey(row, index));
  };

  const startAdd = () => {
    resetEdit();
    if (!tableData) return;

    const today = new Date().toISOString().split('T')[0];
    const newRow: Row = { id: 0 };
    tableData.columns.forEach(col => {
      const n = col.name.toLowerCase();
      if (n === 'id') return;
      if (n === 'investment_id') {
        newRow[col.name] = investments.length > 0 ? investments[0].id : 1;
      } else if (col.type === 'date' || col.type === 'timestamp') {
        newRow[col.name] = today;
      } else if (col.type === 'integer') {
        newRow[col.name] = 0;
      } else if (col.type === 'float' || col.type === 'numeric') {
        newRow[col.name] = 0.0;
      } else {
        newRow[col.name] = '';
      }
    });
    setAddingNew(true);
    setEditMode(true);
    setEditedData(newRow);
  };

  const applyEdit = () => {
    const change: PendingChange = addingNew
      ? {
        id: `add-${Date.now()}`,
        kind: 'add',
        rowKey: `new-${Date.now()}`,
        data: editedData,
        label: `Add row to ${selectedTable}`,
      }
      : {
        id: `edit-${Date.now()}`,
        kind: 'edit',
        rowKey: editingRowKey!,
        data: editedData,
        label: `Edit row ${editedData.id} in ${selectedTable}`,
      };

    setPendingChanges(prev => [...prev, change]);
    showSnack(addingNew ? 'Row queued for insertion' : `Row ${editedData.id} queued for update`, 'info');
    resetEdit();
  };

  const requestDelete = (row: Row, index: number) => {
    setDeleteTarget({ rowKey: rowKey(row, index), row });
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (!deleteTarget) return;
    const change: PendingChange = {
      id: `del-${Date.now()}`,
      kind: 'delete',
      rowKey: deleteTarget.rowKey,
      data: deleteTarget.row,
      label: `Delete row ${deleteTarget.row.id} from ${selectedTable}`,
    };
    setPendingChanges(prev => [...prev, change]);
    showSnack(`Row ${deleteTarget.row.id} queued for deletion`, 'info');
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
  };

  // ── Submit all changes ───────────────────────────────────────────────────

  const submitAll = async () => {
    setSubmitting(true);
    let successCount = 0;
    const errors: string[] = [];
    const remainingChanges: PendingChange[] = [];

    for (const change of pendingChanges) {
      try {
        if (change.kind === 'delete') {
          const id = change.data.id;
          await axios.delete(`/api/edit_data/table/Investments/${selectedTable}/${id}`, {
            params: { cascade: selectedTable.toLowerCase() === 'investments' }
          });
          successCount++;
        } else if (change.kind === 'add') {
          const { id: _, ...payload } = change.data as any; // strip id
          await axios.post(`/api/edit_data/table/Investments/${selectedTable}`, payload);
          successCount++;
        } else if (change.kind === 'edit') {
          await axios.put(`/api/edit_data/table/Investments/${selectedTable}`, change.data);
          successCount++;
        }
      } catch (e: any) {
        const detail = e?.response?.data?.detail || e.message || 'Unknown error';
        errors.push(`${change.label}: ${detail}`);
        remainingChanges.push(change); // Keep failed changes in the queue so they aren't lost
      }
    }

    setPendingChanges(remainingChanges);
    await fetchTableData();
    setSubmitting(false);

    if (errors.length === 0) {
      showSnack(`✅ ${successCount} change${successCount !== 1 ? 's' : ''} committed successfully`, 'success');
    } else {
      showSnack(`⚠ ${successCount} succeeded, ${errors.length} failed.`, 'error');
      setErrorDetails(errors);
      setErrorDialogOpen(true);
    }
  };

  // ── Derived state ────────────────────────────────────────────────────────

  const hasPending = pendingChanges.length > 0;
  const pendingAdds = pendingChanges.filter(c => c.kind === 'add');
  const pendingEdits = pendingChanges.filter(c => c.kind === 'edit');
  const pendingDeletes = pendingChanges.filter(c => c.kind === 'delete');

  const columns = tableData?.columns || [];
  const baseRows: Row[] = tableData?.data || [];

  // Merge pending edits into displayed rows
  const displayRows = baseRows.map((row, i) => {
    const key = rowKey(row, i);
    const edit = pendingChanges.find(c => c.kind === 'edit' && c.rowKey === key);
    return edit ? { ...row, ...edit.data } : row;
  });

  // Prepend pending adds as phantom rows
  const addRows: Row[] = pendingAdds.map((c, i) => ({ ...c.data, id: `pending-add-${i}` as any, _pending_add: true }));
  const allRows: Row[] = [...addRows, ...displayRows];

  const hasInvestmentIdCol = columns.some(c => c.name.toLowerCase() === 'investment_id');

  const menuItems = [
    {
      "heading": "Tools & Analysis",
      "items": ["Dashboard", "Edit Data", "Factsheets", "Property Analysis", "View Metrics", "Monte Carlo"],
      "urls": ["/Investments", "/EditInvestmentData", "/Factsheets", "/PropertyAnalysis", "/ViewInvestmentMetrics", "/ViewInvestmentPredictions"]
    }
  ];

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <ThemeProvider theme={darkMode ? brandingDarkTheme : brandingLightTheme}>
      <div style={{ backgroundColor: darkMode ? '#001E3C' : '#fff', minHeight: '100vh' }}>
        {/* Header bar */}
        <Box sx={{
          position: 'sticky', top: 0, zIndex: 1200,
          background: darkMode ? 'rgba(0,30,60,0.97)' : 'rgba(255,255,255,0.97)',
          backdropFilter: 'blur(8px)',
          borderBottom: '1px solid',
          borderColor: 'divider',
          px: 3, py: 1.5,
          display: 'flex', alignItems: 'center', gap: 2
        }}>
          <DrawerComponent menuItems={menuItems} />
          <IconButton onClick={() => router.push('/Investments')} size="small">
            <KeyboardBackspaceIcon />
          </IconButton>
          <Typography variant="h6" fontWeight={700} sx={{ flex: 1 }}>
            Edit Database Tables
          </Typography>
          {hasPending && (
            <Badge badgeContent={pendingChanges.length} color="warning">
              <Chip
                label={`${pendingChanges.length} pending`}
                color="warning" variant="outlined" size="small"
              />
            </Badge>
          )}
          <Tooltip title="Toggle dark mode">
            <IconButton onClick={() => setDarkMode(d => !d)} size="small">
              {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Tooltip>
        </Box>

        {submitting && <LinearProgress color="success" />}

        <Container maxWidth="xl" sx={{ py: 3 }}>
          <Grid container spacing={2}>
            {/* Controls row */}
            <Grid size={{ xs: 12, sm: 5, md: 4 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Select Table</InputLabel>
                <Select
                  value={selectedTable}
                  label="Select Table"
                  onChange={(e: SelectChangeEvent<string>) => {
                    setSelectedTable(e.target.value);
                    resetEdit();
                    setPendingChanges([]);
                  }}
                  disabled={editMode || hasPending}
                >
                  {tables.map(t => (
                    <MenuItem key={t} value={t}>{t}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, sm: 5, md: 5 }}>
              <TextField
                fullWidth size="small"
                label="Search"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                disabled={editMode || hasPending}
                slotProps={{ input: { endAdornment: <SearchIcon sx={{ color: 'text.secondary', fontSize: 20 }} /> } }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 2, md: 3 }} sx={{ display: 'flex', gap: 1 }}>
              <Tooltip title="Refresh data">
                <span>
                  <IconButton onClick={fetchTableData} disabled={!selectedTable || loading} size="small">
                    <RefreshIcon />
                  </IconButton>
                </span>
              </Tooltip>
              {selectedTable && tableData && (
                <Typography variant="caption" sx={{ alignSelf: 'center', color: 'text.secondary' }}>
                  {tableData.total ?? tableData.total_count ?? 0} rows
                </Typography>
              )}
            </Grid>

            {/* Pending summary bar */}
            {hasPending && (
              <Grid size={12}>
                <Alert
                  severity="info"
                  icon={<InfoOutlinedIcon />}
                  action={
                    <Button color="inherit" size="small" startIcon={<UndoIcon />} onClick={undoLast}>
                      Undo last
                    </Button>
                  }
                  sx={{ '& .MuiAlert-message': { width: '100%' } }}
                >
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                    {pendingAdds.length > 0 && <Chip label={`+${pendingAdds.length} add`} color="warning" size="small" />}
                    {pendingEdits.length > 0 && <Chip label={`✏ ${pendingEdits.length} edit`} color="info" size="small" />}
                    {pendingDeletes.length > 0 && <Chip label={`🗑 ${pendingDeletes.length} delete`} color="error" size="small" />}
                    <Typography variant="caption" sx={{ ml: 'auto' }}>
                      {pendingChanges.slice(-3).map(c => c.label).join(' • ')}
                    </Typography>
                  </Box>
                </Alert>
              </Grid>
            )}

            {/* Table */}
            <Grid size={12}>
              <Paper sx={{ borderRadius: 2, overflow: 'hidden' }}>
                {loading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
                    <CircularProgress />
                  </Box>
                ) : !selectedTable ? (
                  <Box sx={{ textAlign: 'center', py: 8, color: 'text.secondary' }}>
                    <Typography>Select a table to view and edit data</Typography>
                  </Box>
                ) : !tableData ? null : (
                  <Box sx={{ overflow: 'auto', maxHeight: 'calc(100vh - 320px)' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 600 }}>
                      <thead>
                        <tr style={{ position: 'sticky', top: 0, zIndex: 10, background: darkMode ? '#2d2d44' : '#f5f5f5' }}>
                          {columns.map(col => (
                            <th key={col.name} style={{
                              padding: '10px 12px', textAlign: 'left',
                              borderBottom: '2px solid #e0e0e0',
                              fontWeight: 600, fontSize: '0.8rem', letterSpacing: 0.5,
                              whiteSpace: 'nowrap'
                            }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                {col.name}
                                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem' }}>
                                  {col.type}
                                </Typography>
                              </Box>
                            </th>
                          ))}
                          <th style={{ padding: '10px 12px', textAlign: 'left', borderBottom: '2px solid #e0e0e0', width: 120 }}>
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* Add-new inline row at top */}
                        {addingNew && editMode && (
                          <tr style={{ backgroundColor: '#e8f5e9' }}>
                            {columns.map(col => (
                              <td key={col.name} style={{ padding: '10px 12px', borderBottom: '1px solid #e0e0e0' }}>
                                {col.name.toLowerCase() === 'id' ? (
                                  <Typography variant="caption" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>auto</Typography>
                                ) : (
                                  <EditableCell
                                    column={col}
                                    value={editedData[col.name] ?? ''}
                                    onChange={v => setEditedData(prev => ({ ...prev, [col.name]: v }))}
                                    investments={investments}
                                  />
                                )}
                              </td>
                            ))}
                            <td style={{ padding: '10px 12px', borderBottom: '1px solid #e0e0e0' }}>
                              <Chip label="New row" color="success" size="small" variant="outlined" />
                            </td>
                          </tr>
                        )}

                        {allRows.map((row, index) => {
                          const isPendingAdd = Boolean((row as any)._pending_add);
                          const origIndex = isPendingAdd ? -1 : index - pendingAdds.length;
                          const key = isPendingAdd ? `add-${index}` : rowKey(row, origIndex);
                          const isEditingThis = key === editingRowKey && editMode && !addingNew;
                          const isDeleted = pendingChanges.some(c => c.kind === 'delete' && c.rowKey === key);
                          const isEdited = pendingChanges.some(c => c.kind === 'edit' && c.rowKey === key);

                          return (
                            <DataRow
                              key={key}
                              row={row}
                              columns={columns}
                              isEditing={isEditingThis}
                              isDeleted={isDeleted}
                              isAdded={isPendingAdd}
                              isEdited={isEdited}
                              editData={isEditingThis ? editedData : row}
                              onFieldChange={(f, v) => setEditedData(prev => ({ ...prev, [f]: v }))}
                              onEdit={() => startEdit(row, origIndex)}
                              onDelete={() => requestDelete(row, origIndex)}
                              investments={investments}
                              disabled={isEditingThis || (editMode && !isEditingThis)}
                            />
                          );
                        })}
                      </tbody>
                    </table>
                    {allRows.length === 0 && (
                      <Box sx={{ textAlign: 'center', py: 6, color: 'text.secondary' }}>
                        <Typography>No rows found{searchQuery ? ` for "${searchQuery}"` : ''}</Typography>
                      </Box>
                    )}
                  </Box>
                )}
              </Paper>
            </Grid>
          </Grid>
        </Container>

        {/* Sticky bottom action bar */}
        {selectedTable && tableData && (
          <Box sx={{
            position: 'fixed', bottom: 0, left: 0, right: 0,
            bgcolor: 'background.paper',
            borderTop: '1px solid', borderColor: 'divider',
            px: 3, py: 1.5,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            gap: 2, zIndex: 1100,
            boxShadow: '0 -4px 12px rgba(0,0,0,0.08)'
          }}>
            <Button
              variant="text" startIcon={<KeyboardBackspaceIcon />}
              onClick={() => router.push('/Investments')}
              color="inherit" size="small"
            >
              Investments
            </Button>

            <Stack direction="row" spacing={1} alignItems="center">
              {editMode ? (
                <>
                  <Button
                    variant="outlined" color="secondary" size="small"
                    startIcon={<CancelIcon />}
                    onClick={resetEdit}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="contained" color={addingNew ? 'success' : 'primary'} size="small"
                    startIcon={<SaveIcon />}
                    onClick={applyEdit}
                  >
                    {addingNew ? 'Queue Add' : 'Queue Edit'}
                  </Button>
                </>
              ) : hasPending ? (
                <>
                  <Tooltip title="Undo last change">
                    <IconButton size="small" onClick={undoLast}><UndoIcon /></IconButton>
                  </Tooltip>
                  <Button
                    variant="outlined" color="secondary" size="small"
                    onClick={cancelAll}
                  >
                    Cancel All
                  </Button>
                  <Button
                    variant="contained" color="success" size="medium"
                    startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : <CheckCircleIcon />}
                    onClick={submitAll}
                    disabled={submitting}
                  >
                    Commit {pendingChanges.length} Change{pendingChanges.length !== 1 ? 's' : ''}
                  </Button>
                  <Button
                    variant="contained" color="primary" size="small"
                    startIcon={<AddIcon />}
                    onClick={startAdd}
                  >
                    Add Row
                  </Button>
                </>
              ) : (
                <Button
                  variant="contained" color="primary" size="medium"
                  startIcon={<AddIcon />}
                  onClick={startAdd}
                >
                  Add New Row
                </Button>
              )}
            </Stack>
          </Box>
        )}

        {/* Spacer so content isn't hidden behind bottom bar */}
        {selectedTable && <Box sx={{ height: 72 }} />}

        {/* Delete confirm dialog */}
        <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
          <DialogTitle>Confirm Deletion</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Queue row <strong>{deleteTarget?.row.id}</strong> for deletion from <strong>{selectedTable}</strong>?
              The deletion will only happen when you click <em>Commit Changes</em>.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button onClick={confirmDelete} color="error" variant="contained">Queue Delete</Button>
          </DialogActions>
        </Dialog>

        {/* Error details dialog */}
        <Dialog open={errorDialogOpen} onClose={() => setErrorDialogOpen(false)} maxWidth="md" fullWidth>
          <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'error.main' }}>
            <span style={{ fontSize: '1.4rem' }}>⚠️</span> Commit Errors
          </DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb: 2 }}>
              The following operations failed to commit to the database. Failed changes remain in the queue so you can fix them.
            </DialogContentText>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {errorDetails.map((err, i) => (
                <Alert key={i} severity="error" sx={{ fontFamily: 'monospace' }}>
                  {err}
                </Alert>
              ))}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setErrorDialogOpen(false)} color="primary" variant="contained">
              Close
            </Button>
          </DialogActions>
        </Dialog>

        {/* Snack queue */}
        <Snackbar
          key={activeSnack?.key}
          open={snackOpen}
          autoHideDuration={5000}
          onClose={handleSnackClose}
          slotProps={{
            transition: { onExited: () => setActiveSnack(null) }
          }}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
>
          <Alert
            onClose={handleSnackClose}
            severity={activeSnack?.severity || 'info'}
            variant="filled"
            sx={{ width: '100%', maxWidth: 480 }}
          >
            {activeSnack?.message}
          </Alert>
        </Snackbar>
      </div>
    </ThemeProvider>
  );
}

export default EditData;
