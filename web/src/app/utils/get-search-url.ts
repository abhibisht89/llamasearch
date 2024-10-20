export const getSearchUrl = (query: string, search_uuid: string) => {
  const prefix =
    process.env.NODE_ENV === "production" ? "/search.html" : "/search";
  return `${prefix}?q=${encodeURIComponent(query)}&rid=${search_uuid}`;
};

export const getHomeUrl = (query: string, search_uuid: string) => {
  const prefix =
    process.env.NODE_ENV === "production" ? "/index.html" : "/search";
  return `${prefix}?q=${encodeURIComponent(query)}&rid=${search_uuid}`;
};
