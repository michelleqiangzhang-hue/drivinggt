import { Route, Routes } from "react-router-dom";

import Layout from "./components/Layout";
import AccountabilityPage from "./features/accountability/AccountabilityPage";
import CoachPage from "./features/coach/CoachPage";
import CalendarPage from "./features/calendar/CalendarPage";
import DataBankPage from "./features/databank/DataBankPage";
import TodayPage from "./features/today/TodayPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<TodayPage />} />
        <Route path="plan" element={<CalendarPage />} />
        <Route path="account" element={<AccountabilityPage />} />
        <Route path="coach" element={<CoachPage />} />
        <Route path="databank" element={<DataBankPage />} />
      </Route>
    </Routes>
  );
}
